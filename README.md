# mediafire-download

**mediafire-download** is a simple mediafire.com shared files downloader

### Requirements
- **Python 3.10 or greater**
- See `requirements.txt` for additional dependencies. Install with:
  - `python -m pip install -r requirements.txt`
### Usage
##### Install as a module
- `cd mediafire-download`
- `python -m pip install .`
- `python -m mediafire_download [options...] URL [URL...]`
  - where `URL` is a full links to the mediafire.com file
##### Without installing
- `cd mediafire-download`
- Run either:
  - `python mediafire_download/__main__.py [options...] URL [URL...]` OR
  - `mediafire-download.cmd [options...] URL [URL...]` (Windows)
  - `mediafire-download.sh [options...] URL [URL...]` (Linux)


- Invoke `python ... --help` to list options

For bug reports, questions and feature requests use our [issue tracker](https://github.com/trickerer01/mediafire-download/issues)
