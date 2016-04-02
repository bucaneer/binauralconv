A script for converting (surround) audio files into binaural stereo.

## Dependencies
* [python](https://www.python.org/) (version 3)
* [mutagen](https://bitbucket.org/lazka/mutagen)
* [ffmpeg](https://www.ffmpeg.org/) (latest git master recommended, no earlier than 2016-03-29)
* [split2flac](https://github.com/ftrvxmtrx/split2flac)

## Usage

`binauralconv.py [OPTIONS] [PATH]`

By default, binauralconv will:
* concatenate all FLAC files in the directory specified as the last argument (or the current working directory),
* detect the maximum safe volume gain that could be applied during conversion,
* convert the concatenated file into binaural stereo,
* and split it again into individual tracks, using a cue sheet generated from the input files.

Individual steps of the process can be disabled or tuned using options (see `binauralconv.py --help` for full list).

## Examples

```binauralconv.py --ext=".m4a" --no-cue --no-split /path/to/audio```

Concatenate and convert all .m4a files in `/path/to/audio`, but don't generate a cuesheet or split into individual tracks.

```binauralconv.py --dir=. --concatfile=album.wav --cuefile=album.cue```

Use existing audio file and cuesheet instead of generating them from scratch, and perform conversion in current working directory.

```binauralconv.py --baseworkdir=/tmp/binauralconv --splitoutdir=/media/music ~/Documents/suroundstuff```

Convert all FLAC files in `~/Documents/suroundstuff`, placing work files in `/tmp/binauralconv/surroundstuff` and the output in `/media/music`. (Output file/directory pattern based on tags can be configured in `split2flac`)

## License

binauralconv.py is provided under the MIT license.
ClubFritz11.sofa ([source](http://www.sofaconventions.org/mediawiki/index.php/Main_Page)) by Acoustics Research Institute, Austrian Academy of Sciences is licenced under [Creative Commons Attribution-ShareAlike 3.0 Unported License](http://creativecommons.org/licenses/by-sa/3.0/).
