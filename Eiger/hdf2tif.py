#!/usr/bin/env python
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

__author__ = "SasG"
__date__ = "16-11-17"
__version__ = "0.1"

"""
usage: hdf2tif.py [-h] [-o OUTPUT] [-f] [-p] [-s] [-i] files [files ...]

convert EIGER hdf5 image entries to tif files

positional arguments:
  files                 list of master hdf files

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        /path/to/output/basename
  -f, --flatfield       extract flatfield
  -p, --pixelmask       extract pixel mask
  -s, --sum             sum all frames
  -i, --images          extract all image frames
"""

import argparse
import os, sys

# try to import albula from site packages
try:
    from dectris import albula
except Exception as e:
    print("[WARNING] ALBULA API not found in python site-packages, using tifffile and h5py instead.")
    albula = None
finally:
    albula = None

def parseArgs():
    """
    parse user input and return arguments
    """
    parser = argparse.ArgumentParser(description = "convert EIGER hdf5 image entries to tif files")

    parser.add_argument("files", nargs="+", help="list of master hdf files")
    parser.add_argument("-o", "--output", help="/path/to/output/dir", default=None)
    parser.add_argument("-f", "--flatfield", action="store_true", help="extract flatfield")
    parser.add_argument("-p", "--pixelmask", action="store_true", help="extract pixel mask")
    parser.add_argument("-s", "--sum", action="store_true", help="sum image")
    parser.add_argument("-n", "--noAlbula", action="store_true", help="do not use ALBULA API")
    parser.add_argument("-i", "--images", action="store_true", help="extract all image frames")
    parser.add_argument("--h5py", action="store_true", help="force h5py over albula")


    args = parser.parse_args()

    if not any([args.flatfield, args.pixelmask, args.sum, args.images]):
        print("[ERROR] specify a flag")
        parser.print_help()
        sys.exit(1)

    return args

def dataGetter(fname):
    """
    lazy iterator for EIGER h5 data sets
    """
    import h5py
    with h5py.File(fname,"r") as f:
        try:
            data = f["/entry/data/"]
            for dset in sorted(data.keys()):
                for i in range(data[dset].len()):
                    yield data[dset][i,:]
        except Exception as e:
            print("[ERROR] stopping sum", e)
            raise StopIteration

def h5pyConversion(fname, outputBasename, images=False, ff=False, pixelmask=False, summ=False):
    """
    use h5py and tifffile to convert hdf data sets to .tif files
    return the number of saved files
    """
    import h5py
    import tifffile

    imagenumber = 0
    if images:
        for data in dataGetter(fname):
            try:
                output = outputBasename + "_%04d.tif" %imagenumber
                print("[*] saving %s" %output)
                tifffile.imsave(output, data)
                imagenumber += 1
            except Exception as e:
                print(e)
        print("[OK] wrote %s" %output)

    if ff:
        with h5py.File(fname,"r") as f:
            data = f["/entry/instrument/detector/detectorSpecific/flatfield"][:]
            output = outputBasename + "_flatfield.tif"
            tifffile.imsave(output, data)
            print("[OK] wrote %s" %output)
            imagenumber += 1

    if pixelmask:
        with h5py.File(fname,"r") as f:
            data = f["/entry/instrument/detector/detectorSpecific/pixel_mask"][:]
            output = outputBasename + "_pixelmask.tif"
            tifffile.imsave(output, data)
            print("[OK] wrote %s" %output)
            imagenumber += 1

    if summ:
        print("[INFO] summing images, this might take a while")
        tot = None
        data = dataGetter(fname)
        for data in dataGetter(fname):
            try:
                if tot is None:
                    tot = data
                else:
                    tot += data
                output = outputBasename + "_sum.tif"
            except Exception as e:
                print(e)
        tifffile.imsave(output, tot)
        print("[OK] wrote %s" %output)
        imagenumber += 1

    return imagenumber

def albulaConversion(fname, outputBasename, images=False, ff=False, pixelmask=False, summ=False):
    """
    use ALBULA API to convert hdf data sets to .tif files
    return the number of saved files
    """
    imagenumber = 0
    series = albula.DImageSeries(fname)

    if images:
        for i in range(series.first(), series.first() + series.size()):
            output = outputBasename + "_%04d.tif" %i
            print("[*] write %s" %output)
            albula.DImageWriter.write(series[i], output)
            imagenumber += 1

    if pixelmask:
            output = outputBasename + "_pixelmask.tif"
            albula.DImageWriter.write(series[series.first()].optionalData().pixel_mask(), output)
            print("[OK] wrote %s" %output)
            imagenumber += 1

    if summ:
        tot = series[series.first()]
        print("[INFO] summing images, this might take a while")
        for i in range(series.first()+1, series.first() + series.size()):
            tot += series[i]
        output = outputBasename + "_sum.tif"
        albula.DImageWriter.write(tot, output)
        imagenumber += 1

    if ff:
        print("[INFO] fatfield extraction not implemented in ALBULA, trying to use h5py/numpy instead")
        imagenumber += h5pyConversion(fname, outputBasename, ff=True)

    return imagenumber

if __name__ == "__main__":
    args = parseArgs()
    if args.noAlbula:
        albula = None
    filenumber = 1
    for f in args.files:
        basename, _ = os.path.splitext(f)
        if args.output:
            if not os.path.isdir(args.output):
                print("[ERROR] %s is not a existing directory" %args.output)
                sys.exit(1)
            basename = os.path.join(args.output, os.path.basename(basename))

        print("[*] working on %s" %f)
        if albula and not args.h5py:
            imagenumber = albulaConversion(f, basename, args.images, args.flatfield, args.pixelmask, args.sum)
        else:
            imagenumber = h5pyConversion(f, basename, args.images, args.flatfield, args.pixelmask, args.sum)

        print("[*] wrote %d tif files from %s" %(imagenumber,f))
        filenumber += 1
