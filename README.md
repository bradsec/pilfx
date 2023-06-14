# PILFX - Batch Image Transformations and Effects with Python PIL

A Python batch image processing utility which uses the Pillow (PIL) library to apply various image effects and transformations.

## Requirements

- Python 3
- Pillow (PIL)
- Numpy

## Getting Started

1. Clone the repo 
```terminal
git clone https://github.com/bradsec/pilfx
```
2. Place original images into the `src` directory within the newly created pilfx directory. New images will be created in `dst` directory. These default locations can be changes using the -s and -d arguments.

3. Run the command `python3 pilfx.py (options)` as per examples shown below.


## Command-line Usage

```terminal

 ██████╗ ██╗██╗     ███████╗██╗  ██╗
 ██╔══██╗██║██║     ██╔════╝╚██╗██╔╝
 ██████╔╝██║██║     █████╗   ╚███╔╝ 
 ██╔═══╝ ██║██║     ██╔══╝   ██╔██╗ 
 ██║     ██║███████╗██║     ██╔╝ ██╗
 ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝

 [Batch Image Transformations and Effects with Python PIL]

usage: pilfx.py [-h] [-s SRC_DIR] [-d DST_DIR] [-b BLUR] [-c REDUCE_COLORS] [-g] [-i] [-o OPACITY] [-r ROTATE] [--width WIDTH]
                [--height HEIGHT] [--scale SCALE] [--algo ALGO] [--filetype FILETYPE] [--pixelize [PIXELIZE]] [--halftone [HALFTONE]]
                [--dither] [--posterize [POSTERIZE]] [--brightness BRIGHTNESS] [--saturation SATURATION] [--htsample HTSAMPLE]
                [--set_colors SET_COLORS] [--set_trans_colors SET_TRANS_COLORS]

Process images.

optional arguments:
  -h, --help            show this help message and exit
  -s SRC_DIR, --src_dir SRC_DIR
                        Source (src) directory (contains original images to be processed)
  -d DST_DIR, --dst_dir DST_DIR
                        Destination (dst) directory (contains newly created images)
  -b BLUR, --blur BLUR  Base blur factor (ensures consistent blur effect regardless of image size)
  -c REDUCE_COLORS, --reduce_colors REDUCE_COLORS
                        Reduce the amount of colors in the images color palette
  -g, --grayscale       Grayscale
  -i, --invert          Invert colors
  -o OPACITY, --opacity OPACITY
                        Set opacity of final image (values 0.0 to 1.0 with zero being fully transparent)
  -r ROTATE, --rotate ROTATE
                        Rotation angle
  --width WIDTH         New width
  --height HEIGHT       New height
  --scale SCALE         Scale percentage
  --algo ALGO           Change resample algorithm NEAREST = 0, LANCZOS = 1, BILINEAR = 2, BICUBIC = 3, BOX = 4, HAMMING = 5
  --filetype FILETYPE   Output filetype - .png (preserve transparency effects) or .jpg (no transparency, generally smaller file sizes)
  --pixelize [PIXELIZE]
                        Pixelize
  --halftone [HALFTONE]
                        Halftone foreground and background colors
  --dither              Apply FLOYDSTEINBERG dithering
  --posterize [POSTERIZE]
                        Posterize image bits 1-8
  --brightness BRIGHTNESS
                        Brightness
  --saturation SATURATION
                        Saturation
  --htsample HTSAMPLE   Change halftone sample size
  --set_colors SET_COLORS
                        Custom colors or color palette name to replace existing colors
  --set_trans_colors SET_TRANS_COLORS
                        Colors to be made transparent

```

## Example Usage

```terminal
# Resize to a required width maintaining aspect ratio
python3 pilfx.py -width 1920

#  Resize to a required height maintaining aspect ratio
python3 pilfx.py -height 1080

# Note: Setting both width and height will not squash image it will crop to the size unless you have correct aspect ratio.

# Alternative resizing by scaling up or down (by percentage)

# Example for 200% (twice original size)
python3 pilfx.py --scale 200

# Example for 50% (half size)
python3 pilfx.py --scale 50

# Reduce colors in image

# Example reduce to 16 color image
python3 pilfx.py -c 16

# Example reduce to 4 color image
python3 pilfx.py -c 4

# Example reduce to two color image and change colors (use HEX values)
python3 pilfx.py -c 2 --set_colors "#000000,#FFFFFF"

# Example to reduce colors and set one of the colors to transparent
python3 pilfx.py -c 2 --set_colors "#000000,#FFFFFF" --set_trans_colors "#000000"

# Example using color palette defined in `color_palettes.py`
# This method will reduce the image colors by how many are in the named color_palette

python3 pilfx.py --set_colors "cga"
```

```terminal
# Creating a halftone effect (choose two HEX colors)
python3 pilfx.py --halftone "#FFFFFF,#000000"

# Change halftone sample size (circles) default is 10
# Increasing --htsample value will make the pattern larger
python3 pilfx.py --halftone "#FFFFFF,#000000" --htsample 20

# Halftone with transparent background
python3 pilfx.py --halftone "#FFFFFF, none"

# Halftone with original image in background
python3 pilfx.py --halftone "#000000, image"
```

```terminal
# Pixelize image retro effect try different values 64, 128, 256
python3 pilfx.py --pixelize 128

# Can be used with other combinations
python3 pilfx.py --set_colors "c64" --pixelize 128
```

```terminal
# Rotate images with --rotate and angle
python3 pilfx.py --rotate 90
```


## Sample Images

Sample photo credit - [Unsplash](https://unsplash.com/photos/X16zXcbxU4U)

| Command | Resulting Image |
|------------------|------------------|
| `python3 pilfx.py --halftone "#000000, #FFFFFF"`| <img src="dst/car_1920x1280_halftone10_colors_000000_ffffff.png" alt="dst/car_1920x1280_halftone10_colors_000000_ffffff.png" width="400"> |
| `python3 pilfx.py --halftone "#00FF00, #000000" --htsample 20 --scale 150`| <img src="dst/car_2880x1920_halftone20_colors_00ff00_000000.png" alt="dst/car_2880x1920_halftone20_colors_00ff00_000000.png" width="400"> |
| `python3 pilfx.py --set_colors "cga"`| <img src="dst/car_1920x1280_cga_colorpalette_8color_cga_colorpalette.png" alt="dst/car_1920x1280_cga_colorpalette_8color_cga_colorpalette.png" width="400"> |
| `python3 pilfx.py --reduce_colors 16 --pixelize 128`| <img src="dst/car_1920x1280_16color_pixelized128.png" alt="dst/car_1920x1280_16color_pixelized128.png" width="400"> |
| `python3 pilfx.py --scale 50 --rotate 45 --filetype .jpg` | <img src="dst/car_1132x1132_rotated45.jpg" alt="dst/car_1132x1132_rotated45.jpg" width="400"> |
| `python3 pilfx.py --reduce_colors 16 --invert --grayscale --filetype .jpg` | <img src="dst/car_1920x1280_16color_grayscale_invert.jpg" alt="dst/car_1920x1280_16color_grayscale_invert.jpg" width="400"> |

## Color Palettes
A list of predefined color palettes can be found in `color_palettes.py`. Additional palettes can be added you can then use by the name with `--set_colors "palettename"`

