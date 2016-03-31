A script for converting (surround) audio files into binaural stereo.

Dependencies:
* [ffmpeg](https://www.ffmpeg.org/) (latest git master recommended, no earlier than 2016-03-29)
* [split2flac](https://github.com/ftrvxmtrx/split2flac)

Usage: binauralconv.py [OPTIONS] [PATH]

By default, binauralconv will 
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
  gain applied in the sofalizer filter
 
 --volgain=FLT, -volgain=FLT, -g=FLT:
  volume gain to apply
 
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
  file extension to convert (default: .flac)
 
 --dir=DIR, -dir=DIR, -d=DIR:
  working directory (default: [baseworkdir]/[PATH basename])
 
 --no-log, -no-log, -l:
  don't write a log file
 
 --concatfile=FILE, -concatfile=FILE:
  filename of concatenated album (default: concat.flac)
 
 --convfile=FILE, -convfile=FILE:
  filename of converted album (default: concat_b.flac)
 
 --listfile=FILE, -listfile=FILE:
  filename of list file for concatenation (default: filelist.txt)
 
 --cuefile=FILE, -cuefile=FILE:
  filename of cue sheet (default: cuesheet.cue)
 
 --logfile=FILE, -logfile=FILE:
  filename of output log (default: binauralvonv.log)
 
 --baseworkdir=DIR, -baseworkdir=DIR:
  base for the default work directory
 
 --splitoutdir=DIR, -splitoutdir=DIR:
  output directory for split songs
 
 --quad, -quad, -4:
  use quadraphonic speaker layout
 
 --quiet, -quiet, -q:
  quiet mode
 
 --verbose, -verbose, -v:
  verbose mode (show subprocess output)
 
 --help, -help, -h:
  show this message and quit
