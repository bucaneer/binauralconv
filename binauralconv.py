#!/usr/bin/env python3

"""
Copyright (c) 2016, 2017 Justas Lavišius <bucaneer@gmail.com>

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
from os import listdir, chdir, mkdir, remove
from os.path import abspath, basename, dirname, isdir, isfile, join, realpath, split
from shutil import which
import mutagen as mg
from time import strftime
import tempfile as tmp

scriptdir = dirname(realpath(__file__))

quiet = False
verbose = False
force = False
ffmpeg = which("ffmpeg")
splitflac = which("split2flac")
sofafile = join(scriptdir, "ClubFritz11.sofa")
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
generatelfe = False
lfemultiplier = 1.0
subboost = True
volgain = None
volgainoffset = -0.05
rgnormalize = True
replaygain = None
alimit = False
baseworkdir = "/tmp/binauralconv"
splitoutdir = "."
tempfile = None
sofalizer = False

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
		float(x)
		return True
	except ValueError:
		return False

def filtergraph (volume=None):
	if sofalizer:
		speakers51 = "speakers=FL 30 0|FR 330 0|FC 0 0|BL 120 0|BR 240 0|BC 180 0"
		speakers40 = "speakers=FL 45 0|FR 315 0|FC 0 0|BL 135 0|BR 225 0|BC 180 0"
		if layout == "4.0":
			speakers = speakers40
		else:
			speakers = speakers51
	else:
		if layout == "4.0":
			wavs = "\
amovie={dir}/wavs/fl_q.wav[h_fl],amovie={dir}/wavs/fr_q.wav[h_fr],\
amovie={dir}/wavs/fc.wav[h_fc],amovie={dir}/wavs/bc.wav,asplit=2[h_bc][h_lfe],\
amovie={dir}/wavs/bl_q.wav[h_bl],amovie={dir}/wavs/br_q.wav[h_br]".format(dir=scriptdir)
		else:
			wavs = "\
amovie={dir}/wavs/fl.wav[h_fl],amovie={dir}/wavs/fr.wav[h_fr],\
amovie={dir}/wavs/fc.wav[h_fc],amovie={dir}/wavs/bc.wav,asplit=2[h_bc][h_lfe],\
amovie={dir}/wavs/bl.wav[h_bl],amovie={dir}/wavs/br.wav[h_br]".format(dir=scriptdir)
		
		speakers="FL|FR|FC|LFE|BC|SL|SR"
	
	if generatelfe:
		pan = "\
asplit=2 [orig][sub];\
[sub] pan=mono|FC<FC+FR+SL+FL+SR+BL+BR+BC+LFE,firequalizer=gain='if(lt(f,150), 0, -INF)',pan=LFE|LFE=c0 [LFE];\
[orig] pan=FC+FR+SL+FL+SR+BC|FC=FC|FR=FR|SL<SL+BL|FL=FL|SR<SR+BR|BC=LFE [orig2];\
[orig2][LFE] amerge,pan=6.1|FL=c0|FR=c1|FC=c2|LFE={lfemultiplier}*c3|BC=c4|SL=c5|SR=c6".format(lfemultiplier=(0.7*lfemultiplier))
	else:
		pan = "\
asplit=2 [orig][sub];\
[sub] channelsplit=channel_layout=5.1 [FL][FR][FC][LFE][BL][BR];\
[FL][FR][FC][BL][BR] amerge=inputs=5,anullsink;\
[LFE] pan=BC+LFE|LFE=c0|BC=c0,channelsplit=channel_layout=BC+LFE [BC][LFE2];\
[LFE2] firequalizer=gain='if(lt(f,150), 0, -INF)',pan=LFE|LFE=c0 [LFE2];[BC] firequalizer=gain='if(gt(f,150), 0, -INF)',pan=BC|BC=c0 [BC];\
[orig] pan=FC+FR+SL+FL+SR|FC=FC|FR=FR|SL<SL+BL|FL=FL|SR<SR+BR [orig2];\
[orig2][BC][LFE2] amerge=inputs=3,pan=6.1|FL=c0|FR=c1|FC=c2|LFE={lfemultiplier}*c3|BC=c4|SL=c5|SR=c6".format(lfemultiplier=lfemultiplier)
	
	if subboost:
		subeq = "entry(20,2);entry(40,1);entry(55,1.5);entry(60,2.5);entry(75,1);entry(85,0.5);"
	else:
		subeq = ""
	
	maineq = "entry(100,0);entry(140,2);entry(200,-0.5);\
entry(250,0);entry(300,0);entry(400,1.0);entry(550,2);entry(700,2);entry(1000,-0.5);\
entry(1300,-0.5);entry(1700,1);entry(2000,0);entry(2500,-2.0);entry(3000,-4.0);\
entry(3500,-8);entry(4500,-11.0);entry(7500,-1.0);entry(9500,-1.0);\
entry(10000,-3);entry(12000,-4);entry(13000,-3);entry(14000,0);entry(15000,-2.0);entry(20000,0.0)"
	
	if sofalizer:
		graph = "\
{pan},\
aresample=96000:resampler=soxr:precision=28,\
sofalizer=sofa={sofa}:gain={sofagain}:{speakers},\
firequalizer=delay={eqdelay}:accuracy=2:gain_entry='{subeq}{maineq}',\
aresample=48000:resampler=soxr:precision=28".format(pan=pan, sofa=sofafile, 
		sofagain=sofagain, speakers=speakers, eqdelay=eqdelay, subeq=subeq,
		maineq=maineq)
	else:
		graph = "\
{wavs},\
[a:0]{pan},\
aresample=96000:resampler=soxr:precision=28[main],\
[main][h_fl][h_fr][h_fc][h_lfe][h_bc][h_bl][h_br]headphone=map={speakers}:gain={sofagain},\
firequalizer=delay={eqdelay}:accuracy=2:gain_entry='{subeq}{maineq}'".format(wavs=wavs, pan=pan, 
		sofagain=sofagain, speakers=speakers, eqdelay=eqdelay, subeq=subeq, 
		maineq=maineq)
	
	if volume is not None and isfloat(volume):
		graph += ",%s" % oufiltergraph(volume)
	else:
		graph += ",volumedetect,replaygain"
	return graph

def outfiltergraph (volume):
	graph = "volume=%sdB" % float(volume)
	if (alimit):
		graph += ",alimiter=limit=0.999:level=0:asc=0:attack=10:release=10"
	graph += ",aresample=48000:resampler=soxr:precision=28"
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

def mktemp ():
	global tempfile
	filehandle, filename = tmp.mkstemp(prefix='binauralconv-', suffix='.wv')
	if isfile(filename):
		tempfile = filename
	
	if tempfile is None:
		fatal("Could not create temp file")

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
	args = [ffmpeg, "-f", "concat", "-safe", "0", "-i", listfile, "-c:a", "flac", concatfile]
	if force:
		args.insert(-1, "-y")
	process(args)

def makecue ():
	outfile = join(wdir, cuefile)
	if isfile(outfile) and not force:
		log("Cue sheet exists, skipping.")
		return
	foofile = join(split(outfile)[0], "foo_"+split(outfile)[1])
	
	def tag (metadata, tagname):
		return(metadata.get(tagname, [""])[0].replace('"', r'\"'))
	
	files    = filelist()
	metadata = mg.File(files[0])
	album    = tag(metadata, "album")
	date     = tag(metadata, "date")
	genre    = tag(metadata, "genre")
	alartist = tag(metadata, "albumartist") or tag(metadata, "artist")
	
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
		title  = tag(md, "title")
		artist = tag(md, "artist") or tag(md, "albumartist")
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

def voldet_parseline (proc, l):
	global sofagain, volgain, replaygain
	if ("Parsed_sofalizer" in l or "Parsed_headphone" in l) and "samples clipped" in l:
		proc.kill()
		sofagain -= sofagainstep
		log("Sofalizer gain too high, trying %s dB..." % sofagain)
		return
	elif "Parsed_replaygain" in l and "track_gain" in l:
		replaygain = float(l.split(" ")[-2])
	elif "Parsed_volumedetect" in l and "max_volume" in l:
		volgain = -float(l.split(" ")[-2]) + volgainoffset

def voldet ():
	global alimit, replaygain
	
	mktemp()
	
	while volgain is None and replaygain is None and sofagain > 0:
		args = [ffmpeg, "-i", concatfile, "-af", filtergraph(), 
			"-c:a", "wavpack", "-sample_fmt", "fltp", "-y", tempfile]
		process(args, voldet_parseline, (0, -9))

	if volgain is None:
		fatal("Could not find safe volume gain")
	
	if replaygain is not None and replaygain > volgain and rgnormalize:
		alimit = True

def bconv ():
	global replaygain
	
	if isfile(convfile) and not force:
		log("Converted file exists, skipping.")
		return
	
	if (alimit):
		gain = replaygain
	else:
		gain = volgain
	
	if tempfile is not None and isfile(tempfile):
		if (rgnormalize):
			# Dry run - check if any further volume normalization needed
			replaygain = None
			args = [ffmpeg, "-i", tempfile, "-af", outfiltergraph(gain)+',replaygain', "-f", "null", "-"]
			process(args, voldet_parseline, (0, -9))
			if (replaygain > 0):
				gain += replaygain
				log("Additional gain correction: %.2f (total: %.2f)" % (replaygain, gain))
		
		args = [ffmpeg, "-i", tempfile, "-af", outfiltergraph(gain), convfile]
	else:
		args = [ffmpeg, "-i", concatfile, "-af", filtergraph(gain), convfile]
	
	if force:
		args.insert(-1, "-y")
	process(args)
	
	if isfile(tempfile):
		remove(tempfile)

def cuesplit ():
	process([splitflac, convfile, "-cue", cuefile, "-o", splitoutdir])

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
  gain applied in the sofalizer filter (current: {sofagain})
 
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
  working directory (default: {bwdir}/[PATH basename])
 
 --no-log, -no-log, -l:
  don't write a log file
 
 --ffmpeg=FILE, -ffmpeg=FILE:
  path to FFmpeg executable (currrent: {ffmpeg})
 
 --split2flac=FILE, -split2flac=FILE:
  path to split2flac executable (current: {splitflac})
 
 --sofafile=FILE, -sofafile=FILE:
  path to SOFA file (current: {sofa})
 
 --concatfile=FILE, -concatfile=FILE:
  filename of concatenated album (current: {concatfile})
 
 --convfile=FILE, -convfile=FILE:
  filename of converted album (current: {convfile})
 
 --listfile=FILE, -listfile=FILE:
  filename of list file for concatenation (current: {listfile})
 
 --cuefile=FILE, -cuefile=FILE:
  filename of cue sheet (current: {cuefile})
 
 --logfile=FILE, -logfile=FILE:
  filename of output log (current: {logfile})
 
 --baseworkdir=DIR, -baseworkdir=DIR:
  base for the default work directory (current: {bwdir})
 
 --splitoutdir=DIR, -splitoutdir=DIR:
  output directory for split songs (current: {splitout})
 
 --quad, -quad, -4:
  use quadraphonic speaker layout
 
 --generate-lfe, -generate-lfe:
  replace LFE channel with one generated by a lowpass filter (for 5.0 mixes)
 
 --lfe-multiplier=FLT, -lfe-multiplier=FLT:
  adjust gain of LFE channel (current: {lfemultiplier})
  
 --subboost, -subboost ||
 --no-subboost, -no-subboost:
  (do not) apply extra gain on <100Hz frequencies via equalizer (current: {subboost})
 
 --sofalizer, -sofalizer ||
 --no-sofalizer, -no-sofalizer:
  (do not) use sofalizer FFmpeg filter instead of headphone (current: {sofalizer})

 --normalize, -normalize ||
 --no-normalize, -no-normalize:
  (do not) normalize output to be at least as loud as ReplayGain reference (surrent: {normalize})
 
 --quiet, -quiet, -q:
  quiet mode
 
 --verbose, -verbose, -v:
  verbose mode (show subprocess output)
 
 --help, -help, -h:
  show this message and quit
""".format(exe=exe, ext=fileext, sofagain=sofagain, sofa=sofafile, ffmpeg=ffmpeg, 
		splitflac=splitflac, concatfile=concatfile, convfile=convfile,
		listfile=listfile, cuefile=cuefile, logfile=logfile, bwdir=baseworkdir,
		splitout=splitoutdir, lfemultiplier=lfemultiplier,
		subboost=("subboost" if subboost else "no-subboost"),
		sofalizer=("sofalizer" if sofalizer else "no-sofalizer"),
		normalize=("normalize" if rgnormalize else "no-normalize")))
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
		elif argname in ("--ffmpeg", "-ffmpeg"):
			ffmpeg = param
		elif argname in ("--split2flac", "-split2flac"):
			splitflac = param
		elif argname in ("--sofafile", "-sofafile"):
			sofafile = param
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
		elif argname in ("--generate-lfe", "-generate-fle"):
			generatelfe = True
		elif argname in ("--lfe-multiplier", "-lfe-multiplier"):
			if isfloat(param):
				lfemultiplier = float(param)
			else:
				log("Invalid value for LFE multiplier, ignoring")
		elif argname in ("--subboost", "-subboost"):
			subboost = True
		elif argname in ("--no-subboost", "-no-subboost"):
			subboost = False
		elif argname in ("--sofalizer", "-sofalizer"):
			sofalizer = True
		elif argname in ("--no-sofalizer", "-no-sofalizer"):
			sofalizer = False
		elif argname in ("--normalize", "-normalize"):
			rgnormalize = True
		elif argname in ("--no-normalize", "-no-normalize"):
			rgnormalize = False
		elif isdir(argname):
			path = abspath(argname)
			break
		else:
			log("Unknown argument: %s" % arg)
	
	if path is None:
		path = abspath(".")
	
	if (doconcat or dovolgain or dobconv) and not which(ffmpeg):
		fatal("Wrong FFmpeg path: %s" % ffmpeg)
	
	if dosplit and not which(splitflac):
		fatal("Wrong split2flac path: %s" % splitflac)
	
	if (dovolgain or dobconv) and not isfile(sofafile):
		fatal("SOFA file not found.")
	
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
	log("Layout: %s" % layout)
	log("Generate LFE? %s" % ("yes" if generatelfe else "no"))
	log("Subboost? %s" % ("yes" if subboost else "no"))
	log("SOFA gain: %.2f" % sofagain)
	log("LFE multiplier: %.2f" % lfemultiplier)
	log("Sofalizer? %s" % ("yes" if sofalizer else "no"))
	
	if domakecue:
		log("### Making CUE sheet...")
		makecue()
		log("### Making CUE sheet - done.")
	
	if doconcat:
		log("### Concatenating...")
		concat()
		log("### Concatenating - done.")
	
	if dovolgain and volgain is None:
		log("### Converting (pass 1)...")
		voldet()
		log("### Converting (pass 1) - done. (gain = %.2f (%s))" % ((replaygain if alimit else volgain), 'rg) (vol = %.2f' % volgain if alimit else 'vol'))
	
	if dobconv:
		log("### Converting (pass 2)...")
		bconv()
		log("### Converting (pass 2) - done.")
	
	if dosplit:
		log("### Splitting...")
		cuesplit()
		log("### Splitting - done.")
	
	log("### Done.")

