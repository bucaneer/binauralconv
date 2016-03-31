#!/usr/bin/env python3

"""
Copyright (c) 2016 Justas Lavišius <bucaneer@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import subprocess as sp
from os import listdir, chdir, mkdir
from os.path import abspath, basename, isdir, isfile, join, split
import mutagen as mg
from time import strftime

quiet = False
verbose = False
force = False
fileext = ".flac"
concatfile = "concat.flac"
convfile = "concat_b.flac"
listfile = "filelist.txt"
cuefile = "cuesheet.cue"
logfile = "binauralconv.log"
sofagain = 20.5
sofagainstep = 1.0
eqdelay = 0.2
layout = "5.1"
volgain = None
volgainoffset = -0.05
baseworkdir = "/media/storage/SURROUND RAW"
splitoutdir = "/media/storage/MUZIKA/BINAURAL"

class Logger ():
	def __init__ (self):
		self.stdout = sys.stdout
		try:
			self.log = open(logfile, "a")
		except Exception as e:
			fatal("Could not open log file: %s" % repr(e))
	
	def write (self, msg):
		self.stdout.write(msg)
		self.log.write(msg)
		self.flush()
	
	def flush (self):
		self.stdout.flush()
		self.log.flush()

def fatal (msg):
	print("[%s] %s" % (strftime("%x %X"), msg))
	sys.exit(1)

def log (msg):
	if quiet: return
	print("[%s] %s" % (strftime("%x %X"), msg))

def isfloat (x):
	try:
		return True
	except ValueError:
		return False

def filtergraph (volume=None):
	speakers51 = "speakers=FL 30 0|FR 330 0|FC 0 0|BL 120 0|BR 240 0|BC 180 0"
	speakers40 = "speakers=FL 45 0|FR 315 0|FC 0 0|BL 135 0|BR 225 0|BC 180 0"
	if layout == "4.0":
		speakers = speakers40
	else:
		speakers = speakers51
	graph = "\
pan=hexagonal|FL=FL|FR=FR|FC=FC|BC=LFE|BL<SL+BL|BR<SR+BR,\
aresample=96000:resampler=soxr:precision=28,\
sofalizer=sofa=/home/justas-arch/.config/mpv/ClubFritz11.sofa:gain=%s:%s,\
firequalizer=delay=%s:gain_entry='entry(0,0);entry(40,1);entry(55,1);\
entry(75,6);entry(120,2);entry(250,0);entry(400,0);entry(1700,-1);\
entry(2000,-4);entry(4500,-11);entry(7500,-3);entry(9500,-3);\
entry(10000,-4);entry(12000,-4);entry(14000,0);entry(15000,-3);entry(20000,0)',\
aresample=48000:resampler=soxr:precision=28" % (sofagain, speakers, eqdelay)
	if volume is not None and isfloat(volume):
		graph += ",volume=%sdB" % float(volume)
	else:
		graph += ",volumedetect"
	return graph

def process (args, linefunc=None, exitcodes=(0,)):
	proc = sp.Popen(args, stdout=sp.PIPE, stderr=sp.STDOUT, stdin=sp.DEVNULL)
	err = ""
	for line in iter(proc.stdout.readline,b''):
		l = line.decode().rstrip()
		err += l
		if verbose:
			print(l)
		if linefunc is not None:
			linefunc(proc, l)
	proc.wait()
	if proc.returncode not in exitcodes:
		msg = "Process ended unexpectedly (return code %s)" % proc.returncode
		if not verbose:
			msg += ":\n%s" % err
		fatal(msg)

def filelist ():
	files = sorted([join(path, f) for f in listdir(path) if isfile(join(path, f)) and f[-len(fileext):].lower() == fileext])
	if not files: 
		fatal("No %s files found in %s" % (fileext, path))
	return files

def concat ():
	if isfile(listfile) and not force:
		log("List file exists, skipping.")
	else:
		files = filelist()
		try:
			with open(listfile, "w") as l:
				l.write(''.join(["file '%s'\nduration %s\n" % (f.replace("'","'\\''"), mg.File(f).info.length) for f in files]))
		except Exception as e:
			fatal("Could not create list file: %s" % repr(e))
	if isfile(concatfile) and not force:
		log("Concatenated file exists, skipping.")
		return
	args = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", listfile, "-c:a", "flac", concatfile]
	if force:
		args.insert(-1, "-y")
	process(args)

def makecue ():
	outfile = join(wdir, cuefile)
	if isfile(outfile) and not force:
		log("Cue sheet exists, skipping.")
		return
	foofile = join(split(outfile)[0], "foo_"+split(outfile)[1])
	
	files    = filelist()
	metadata = mg.File(files[0])
	album    = metadata.get("album", [""])[0]
	date     = metadata.get("date",  [""])[0]
	genre    = metadata.get("genre", [""])[0]
	alartist = metadata.get("albumartist", [""])[0] or metadata.get("artist", [""])[0]
	
	cueheader = ""
	cueheader += 'REM GENRE "%s"\n' % genre    if genre    else ""
	cueheader += 'REM DATE %s\n'    % date     if date     else ""
	cueheader += 'PERFORMER "%s"\n' % alartist if alartist else ""
	cueheader += 'TITLE "%s"\n'     % album    if album    else ""
	cueheader += 'FILE "%s" WAVE\n' % convfile
	
	cuetext     = cueheader
	cuetext_foo = cueheader
	
	def timestamp (sec, foobar=False):
		minutes = "%0#2d" % (sec // 60)
		seconds = "%0#2d" % (sec % 60)
		if foobar:
			frames  = "%0#2d" % int((sec % 1) * 75)
			return "%s:%s:%s" % (minutes, seconds, frames)
		else:
			msecs   = "%0#3d" % int((sec % 1) * 1000)
			return "%s:%s.%s" % (minutes, seconds, msecs)
	
	time = 0
	offset = eqdelay
	
	for i in range(len(files)):
		cuetrack = ""
		index = "%0#2d" % (i+1)
		md = mg.File(files[i])
		title  = md.get("title",  [""])[0]
		artist = md.get("artist", [""])[0] or md.get("albumartist", [""])[0]
		length = md.info.length
		cuetrack += '  TRACK %s AUDIO\n'   % index
		cuetrack += '    TITLE "%s"\n'     % title  if title  else ""
		cuetrack += '    PERFORMER "%s"\n' % artist if artist else ""
		
		cuetext     += cuetrack
		cuetext_foo += cuetrack
		
		tstamp = timestamp(time)
		if time == 0:
			time += offset
			cuetext     += '    INDEX 00 %s\n'% timestamp(offset)
			cuetext_foo += '    INDEX 00 %s\n'% timestamp(offset, True)
		cuetext     += '    INDEX 01 %s\n'    % tstamp
		cuetext_foo += '    INDEX 01 %s\n'    % timestamp(time, True)
		time += length
	
	try:
		with open(outfile, "w") as f:
			f.write(cuetext)
	except Exception as e:
		fatal("Could not write output to file: %s" % repr(e))
		
	try:
		with open(foofile, "w") as f:
			f.write(cuetext_foo)
	except Exception as e:
		fatal("Could not write output to file: %s" % repr(e))

def voldet ():
	def parseline (proc, l):
		global sofagain, volgain
		if "Parsed_sofalizer" in l and "samples clipped" in l:
			proc.kill()
			sofagain -= sofagainstep
			log("Sofalizer gain too high, trying %s dB..." % sofagain)
			return
		elif "Parsed_volumedetect" in l and "max_volume" in l:
			volgain = -float(l.split(" ")[-2]) + volgainoffset
			return
	
	while volgain is None and sofagain > 0:
		args = ["ffmpeg", "-i", concatfile, "-af", filtergraph(), 
			"-f", "null", "/dev/null"]
		process(args, parseline, (0, -9))

	if volgain is None:
		fatal("Could not find safe volume gain")

def bconv ():
	if isfile(convfile) and not force:
		log("Converted file exists, skipping.")
		return
	args = ["ffmpeg", "-i", concatfile, "-af", filtergraph(volgain), convfile]
	if force:
		args.insert(-1, "-y")
	process(args)

def cuesplit ():
	process(["split2flac", convfile, "-cue", cuefile, "-o", splitoutdir])

if __name__ == '__main__':
	path = None
	wdir = None
	logtofile = True
	doconcat = True
	domakecue = True
	dovolgain = True
	dobconv = True
	dosplit = True
	
	for arg in sys.argv[1:]:
		splitarg = arg.split("=", maxsplit=1)
		argname = splitarg[0]
		param = splitarg[1] if len(splitarg)>1 else None
			
		exe = sys.argv[0] if isfile(sys.argv[0]) else "binauralconv"
		if argname in ("--help", "-help", "-h"):
			print(\
"""\
Usage: {exe} [OPTIONS] [PATH]

By default, binauralconv will:
* concatenate all FLAC files in the directory specified as the last argument (or the current working directory),
* detect the maximum safe volume gain that could be applied during conversion,
* convert the concatenated file into binaural stereo,
* and split it again into individual tracks, using a cue sheet generated from the input files.

Individual steps of the process can be disabled or tuned using these options:

 --no-concat, -no-concat, -t:
  don't concatenate files
 
 --concat-only, -concat-only:
  only perform concatenation
 
 --no-cue, -no-cue, -c:
  don't generate cue sheet
 
 --cue-only, -cue-only:
  only generate cue sheet
 
 --sofagain=FLT, -sofagain=FLT:
  gain applied in the sofalizer filter (default: {sofagain})
 
 --volgain=FLT, -volgain=FLT, -g=FLT:
  volume gain to apply (default: detected automatically)
 
 --voldetect-only, -voldetect-only:
  only perform safe volume gain detection
 
 --no-conv, -no-conv, -n:
  don't convert to binaural
 
 --conv-only, -conv-only:
  only convert to binaural
 
 --no-split, -no-split, -s:
  don't split into individual tracks
 
 --split-only, -split-only:
  only split into individual tracks
 
 --ext=EXT, -ext=EXT, -x=EXT:
  file extension to convert (default: {ext})
 
 --dir=DIR, -dir=DIR, -d=DIR:
  working directory (default: [baseworkdir]/[PATH basename])
 
 --no-log, -no-log, -l:
  don't write a log file
 
 --concatfile=FILE, -concatfile=FILE:
  filename of concatenated album (default: {concatfile})
 
 --convfile=FILE, -convfile=FILE:
  filename of converted album (default: {convfile})
 
 --listfile=FILE, -listfile=FILE:
  filename of list file for concatenation (default: {listfile})
 
 --cuefile=FILE, -cuefile=FILE:
  filename of cue sheet (default: {cuefile})
 
 --logfile=FILE, -logfile=FILE:
  filename of output log (default: {logfile})
 
 --baseworkdir=DIR, -baseworkdir=DIR:
  base for the default work directory (default: {bwdir})
 
 --splitoutdir=DIR, -splitoutdir=DIR:
  output directory for split songs (default: {splitout})
 
 --quad, -quad, -4:
  use quadraphonic speaker layout
 
 --quiet, -quiet, -q:
  quiet mode
 
 --verbose, -verbose, -v:
  verbose mode (show subprocess output)
 
 --help, -help, -h:
  show this message and quit
""".format(exe=exe, ext=fileext, sofagain=sofagain, concatfile=concatfile, convfile=convfile, 
		listfile=listfile, cuefile=cuefile, logfile=logfile, bwdir=baseworkdir, 
		splitout=splitoutdir))
			sys.exit(0)
		elif argname in ("--no-concat", "-no-concat", "-t"):
			doconcat = False
		elif argname in ("--no-cue", "-no-cue", "-c"):
			domakecue = False
		elif argname in ("--volgain", "-volgain", "-g"):
			if isfloat(param):
				volgain = float(param)
			else:
				log("Invalid value for volume gain, ignoring")
		elif argname in ("--sofagain", "-sofagain"):
			if isfloat(param):
				sofagain = float(param)
			else:
				log("Invalid value for volume gain, ignoring")
		elif argname in ("--no-conv", "-no-conv", "-n"):
			dobconv = False
		elif argname in ("--no-split", "-no-split", "-s"):
			dosplit = False
		elif argname in ("--ext", "-ext", "-x"):
			fileext = param.lower()
		elif argname in ("--no-log", "-no-log", "-l"):
			logtofile = False
		elif argname in ("--concatfile", "-concatfile"):
			concatfile = param
		elif argname in ("--convfile", "-convfile"):
			convfile = param
		elif argname in ("--listfile", "-listfile"):
			listfile = param
		elif argname in ("--cuefile", "-cuefile"):
			cuefile = param
		elif argname in ("--logfile", "-logfile"):
			logfile = param
		elif argname in ("--baseworkdir", "-baseworkdir"):
			baseworkdir = param
		elif argname in ("--splitoutdir", "-splitoutdir"):
			splitoutdir = param
		elif argname in ("--concat-only", "-concat-only"):
			doconcat = True
			domakecue = False
			dovolgain = False
			dobconv = False
			dosplit = False
		elif argname in ("--cue-only", "-cue-only"):
			doconcat = False
			domakecue = True
			dovolgain = False
			dobconv = False
			dosplit = False
		elif argname in ("--conv-only", "-conv-only"):
			doconcat = False
			domakecue = False
			dovolgain = False
			dobconv = True
			dosplit = False
		elif argname in ("--split-only", "-split-only"):
			doconcat = False
			domakecue = False
			dovolgain = False
			dobconv = False
			dosplit = True
		elif argname in ("--quiet", "-quiet", "-q"):
			quiet = True
			verbose = False
		elif argname in ("--verbose", "-verbose", "-v"):
			verbose = True
			quiet = False
		elif argname in ("--dir", "-dir", "-d"):
			wdir = param
		elif argname in ("--force", "-force", "-f"):
			force = True
		elif argname in ("--quad", "-quad", "-4"):
			layout = "4.0"
		elif isdir(argname):
			path = abspath(argname)
			break
		else:
			log("Unknown argument: %s" % arg)
	
	if path is None:
		path = abspath(".")
	
	if wdir is None:
		wdir = join(baseworkdir, basename(path))
	if isdir(wdir):
		chdir(wdir)
	else:
		try:
			mkdir(wdir)
			chdir(wdir)
		except Exception as e:
			fatal("Could not create working directory: %s" % repr(e))
	
	if logtofile:
		sys.stdout = Logger()
	
	log("Path: %s" % path)
	log("Wdir: %s" % wdir)
	
	if doconcat:
		log("### Concatenating...")
		concat()
		log("### Concatenating - done.")
	
	if domakecue:
		log("### Making CUE sheet...")
		makecue()
		log("### Making CUE sheet - done.")
	
	if dovolgain and volgain is None:
		log("### Running volume detection...")
		voldet()
		log("### Running volume detection - done. (volgain = %.2f)" % volgain)
	
	if dobconv:
		log("### Converting...")
		bconv()
		log("### Converting - done.")
	
	if dosplit:
		log("### Splitting...")
		cuesplit()
		log("### Splitting - done.")
	
	log("### Done.")
