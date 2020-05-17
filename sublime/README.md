# Using PDPy11 with Sublime

## Build system

1. Copy `PDPy11.sublime-build` file to sublime package directory. To open this directory, press *Preferences* -> *Browse packages* and then go to `User` directory.
2. In `PDPy11.sublime-build` file, change `<path_to_pdpy11>` to the correct path, like: `~/Documents/pdpy11`. Make sure the directory is named `pdpy11`, not `PDPy11` or `PDPy11-master`. If you're using Windows, don't forget to escape backslashes like `C:\\Users\\Ivanq\\Documents\\pdpy11` or use forward slashes like `C:/Users/Ivanq/Documents/pdpy11`.
3. Then, in case you're using MacOS or Linux, or any other \*nix system, make `pdpy11/sublime/subl.sh` executable by issuing `chmod +x path/to/pdpy11/sublime/subl.sh`.
4. Optionally, you can enable BK2010 emulator support by uncommenting a few lines in either `pdpy11/sublime/subl.sh` (MacOS and \*nix) or `pdpy11/sublime/subl.bat` (Windows) and replacing `/path/to/bk2010` or `C:\path\to\bk2010` with the correct path.
5. You're now ready to go. Open some *.mac* file and press `Ctrl + B`, or `Ctrl + Shift + B` in case you have several build systems for *.mac* files.


## Syntax highlighting

1. Copy `PDPy11.sublime-syntax` and `PDPy11.sublime-color-scheme` files to sublime package directory. To open this directory, press *Preferences* -> *Browse packages* and then go to `User` directory.
2. Open any *.mac* file and choose *User* -> *PDPy11* in the language list (at the bottom right of the editor). Then open *Preferences* -> *Color Scheme...* and choose *PDPy11*.