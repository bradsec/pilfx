import argparse
import logging
import os
import sys
import random
from math import sqrt
from typing import List, Optional
from pathlib import Path

import numpy as np
from PIL import (
    Image,
    ImageColor,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageOps,
)
from tqdm import tqdm

from color_palettes import COLOR_PALETTES

Image.MAX_IMAGE_PIXELS = None
logging.basicConfig(level=logging.INFO, format='%(message)s')

class BatchPILFX:
    def __init__(self, args: argparse.Namespace, htsample = 10, htscale = 1, htprocessing_scale = 1):
        self.args = args
        self.htsample = htsample
        self.htscale = htscale * htprocessing_scale
        self.htprocessing_scale = htprocessing_scale
        self.filename_addon = None
        self.original_width = None
        self.original_height = None
        self.width = None
        self.height = None
        self.backgrond = None
        self.foreground = None
        self.image = None
        self.draw = None
        self.resample_algorithm = args.algo
        self.shuffle_colors = args.shuffle_colors
        self.src_dir = args.src_dir
        self.dst_dir = args.dst_dir or args.src_dir
        os.makedirs(self.dst_dir, exist_ok=True)
        self.image_files = self.get_image_files()

    def get_image_files(self) -> List[Path]:
        """Get a list of image files in the provided directory."""
        return [file for file in Path(self.src_dir).iterdir() if file.suffix.lower() in (".jpg", ".jpeg", ".png")]
    
    def convert_to_grayscale(self, image: Image) -> Image:
        return image.convert("L")

    def dither_image(self, image: Image) -> Image:
        return image.convert("1", dither=Image.FLOYDSTEINBERG)

    def reduce_colors(self, image: Image, reduce_colors: int, set_colors) -> Image:
        image = image.convert("RGB")
        return self.quantize_image(image, reduce_colors, set_colors)

    def invert_image(self, image: Image) -> Image:
        image = image.convert("RGB")
        return ImageOps.invert(image)

    def adjust_brightness(self, image: Image, brightness: float) -> Image:
        image = image.convert("RGB")
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(brightness)

    def adjust_saturation(self, image: Image, saturation: float) -> Image:
        image = image.convert("RGB")
        enhancer = ImageEnhance.Color(image)
        return enhancer.enhance(saturation)

    def image_blur(self, image: Image, base_blur_factor: float) -> Image:
        width, height = image.size
        image_area = width * height
        self.filename_addon += f"_blur{base_blur_factor}"
        blur_factor = base_blur_factor * (sqrt(image_area) / (100 * sqrt(100)))
        return image.filter(ImageFilter.GaussianBlur(blur_factor))

    def rotate_image(self, image: Image, rotation: int) -> Image:
        if rotation not in [90, 180, 270]:
            image = image.convert("RGBA")
            image = image.rotate(rotation, expand=True, fillcolor=(0, 0, 0, 0))
            self.width, self.height = image.size
            return image
        else:
            image = image.rotate(rotation, expand=True, fillcolor="white")
            self.width, self.height = image.size
            return image
   
    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert HEX color value to RGB"""
        hex_color = hex_color.lstrip('#')
        try:
            if len(hex_color) == 6:
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
        raise ValueError(f"Invalid hexadecimal color code: {hex_color}")
    
    def get_color_values(self, colors_string: str) -> List[str]:
        """Process a string of HEX colors and return a list"""
        colors_string_lower = colors_string.lower()
        
        if colors_string_lower in [palette.lower() for palette in COLOR_PALETTES]:
            color_values = COLOR_PALETTES[next(palette for palette in COLOR_PALETTES if palette.lower() == colors_string_lower)]
            self.filename_addon += f"_{colors_string.lower()}_colorpalette"
        else:
            color_values = [color.strip() for color in colors_string.split(",")]
            colors_string = '_'.join(color[1:] for color in color_values)
            self.filename_addon += f"_colors_{colors_string.lower()}"
        
        if self.shuffle_colors:
            random.shuffle(color_values)
        
        return color_values

    def quantize_image(self, image: Image, quantize_num_colors: int, set_colors: Optional[str] = None) -> Image:
        """Reduce amount of colors in image and/or replace colors in the image."""
        colors = []
        image = image.convert("RGB")
        if set_colors:
            color_values = self.get_color_values(set_colors)
            for color in color_values:
                try:
                    color = ImageColor.getrgb(color)
                    colors.append(color)
                except ValueError:
                    logging.error(f"Invalid color specifier: {color}")
        else:
            color_values = []

        if colors:
            num_colors = len(colors)
            if num_colors < quantize_num_colors:
                group_size = quantize_num_colors // num_colors
                remaining_colors = quantize_num_colors % num_colors
                grouped_colors = []
                for color in colors:
                    for _ in range(group_size):
                        grouped_colors.append(color)
                grouped_colors += colors[:remaining_colors]
                quantized_colors = [(int(c[0]), int(c[1]), int(c[2])) for c in grouped_colors]
            else:
                quantized_colors = [(int(c[0]), int(c[1]), int(c[2])) for c in colors[:quantize_num_colors]]

            # Generate new palette
            new_palette = sum(quantized_colors, ())

            # Apply posterize operation
            image = image.convert("P", palette=Image.ADAPTIVE, colors=quantize_num_colors)

            # Set new palette
            image.putpalette(new_palette)

            # Convert image back to RGB
            image = image.convert("RGB")
        else:
            image = image.quantize(colors=quantize_num_colors)

        return image

    def process_block(self, x, y):
        """Required by create_halftone."""
        total = 0
        count = 0

        for i in range(x, min(x + self.htsample, self.width)):
            for j in range(y, min(y + self.htsample, self.height)):
                pixel = self.image.getpixel((i, j))
                if isinstance(pixel, tuple):  # Color image
                    total += sum(pixel[:3])
                else:  # Grayscale image
                    total += pixel
                count += 1

        if count > 0:
            avg = total // count
            radius = int((1 - avg / 255) * self.htsample / 2 * self.htprocessing_scale * 0.9)  # Scale up the radius and reduce it to 90% of the block size
            if self.foreground:
                fill_color = self.hex_to_rgb(self.foreground)  # Use the specified hex color
            elif self.background.lower() == 'image':
                fill_color = None  # No fill color if the background is an image
            else:
                fill_color = self.hex_to_rgb(self.background)

            # Draw the circle from the center of the block and divide the radius by htprocessing_scale
            if fill_color is not None:
                self.draw.ellipse([(x + self.htsample/2 - radius/self.htprocessing_scale) * self.htscale, 
                                (y + self.htsample/2 - radius/self.htprocessing_scale) * self.htscale, 
                                (x + self.htsample/2 + radius/self.htprocessing_scale) * self.htscale, 
                                (y + self.htsample/2 + radius/self.htprocessing_scale) * self.htscale], fill=fill_color)


    def create_halftone(self, image: Image, foreground: str, background: str) -> Image:
        """Create a halftone version of image."""
        self.image = image
        self.background = background
        self.foreground = foreground
        self.width, self.height = self.image.size

        self.htprocessing_scale = round(max(self.width / self.original_width, self.height / self.original_height))
        self.htscale = self.htprocessing_scale

        if self.background == 'image':
            bg_image = self.image.resize((self.width * self.htscale, self.height * self.htscale))
            bg_image = bg_image.quantize(colors=16).convert('RGBA')
            self.output = Image.new("RGBA", (self.width * self.htscale, self.height * self.htscale))
            self.output.paste(bg_image)
        elif self.background is None or self.background == "":
            self.output = Image.new("RGBA", (self.width * self.htscale, self.height * self.htscale))
        else:
            background_color = self.hex_to_rgb(self.background)
            self.output = Image.new("RGB", (self.width * self.htscale, self.height * self.htscale), color=background_color)

        self.draw = ImageDraw.Draw(self.output)

        self.image = self.image.convert("L")  # Convert to grayscale
        self.image = self.image.convert("1", dither=Image.FLOYDSTEINBERG)

        for x in range(0, self.width, self.htsample):
            for y in range(0, self.height, self.htsample):
                self.process_block(x, y)

        self.image = self.image.convert("L")  # Convert to grayscale
        self.image = self.image.convert("1", dither=Image.FLOYDSTEINBERG)

        self.draw = ImageDraw.Draw(self.output)

        for x in range(0, self.width, self.htsample):
            for y in range(0, self.height, self.htsample):
                self.process_block(x, y)

        if self.htprocessing_scale > 1:
            resized_output = self.output.resize((int(self.width * self.htscale), int(self.height * self.htscale)), self.resample_algorithm)
            resized_output = resized_output.resize((self.width, self.height), self.resample_algorithm)
            return resized_output
        else:
            return self.output


    def posterize_image(self, image: Image, bits: int = 1) -> Image:
        """Apply posterize effect to the image based on bits."""
        if bits < 1 or bits > 8:
            raise ValueError("Invalid number of bits. Must be between 1 and 8.")
            
        # Ensure the image is in RGB mode.
        image = image.convert("RGB")
        image = ImageOps.posterize(image, bits)

        return image
    

    def transparent_colors(self, image: Image, trans_colors: str) -> Image:
        """Make the specified colors transparent in the image."""
        if trans_colors:
            if image.mode != 'RGBA':
                image = image.convert("RGBA")

            data = np.array(image)
            red, green, blue, alpha = data.T

            colors = [color.strip() for color in trans_colors.split(',')]

            for color in colors:
                color_rgb = ImageColor.getrgb(color)

                # Change all pixels (also shades) of the trans_color to be transparent
                color_areas = (red == color_rgb[0]) & (green == color_rgb[1]) & (blue == color_rgb[2])
                data[..., :3][color_areas.T] = (0, 0, 0)  # Change color to black
                data[..., 3][color_areas.T] = 0  # Change Alpha to 0

            image = Image.fromarray(data)

        return image


    def crop_resize_image(self, image: Image, new_width: int = 0, new_height: int = 0, scale_percentage: int = 0) -> Image:
        """
        Crop and resize the image based on the provided dimensions and resize algorithm.
        If only new_width or new_height is provided, the other dimension will be calculated
        to maintain the aspect ratio of the original image.
        If both new_width and new_height are provided, the image will be resized first
        to maintain the aspect ratio and then cropped to the desired dimensions.
        If neither new_width nor new_height is provided, the original dimensions will be maintained.
        If scale_percentage is specified, the image will be scaled up or down based on the percentage.
        The self.resample_algorithm parameter allows specifying the resize algorithm (default: Image.LANCZOS).
        """
        width, height = image.size

        if new_width > 0 or new_height > 0:
            if new_width > 0 and new_height == 0:
                new_height = int((new_width / width) * height)
            elif new_height > 0 and new_width == 0:
                new_width = int((new_height / height) * width)
            elif new_width > 0 and new_height > 0:
                new_aspect_ratio = new_width / new_height
                old_aspect_ratio = width / height

                if new_aspect_ratio > old_aspect_ratio:
                    temp_new_height = int(new_width / old_aspect_ratio)
                    image = image.resize((new_width, temp_new_height), resample=self.resample_algorithm)
                else:
                    temp_new_width = int(new_height * old_aspect_ratio)
                    image = image.resize((temp_new_width, new_height), resample=self.resample_algorithm)

                left = (image.width - new_width) / 2
                top = (image.height - new_height) / 2
                right = (image.width + new_width) / 2
                bottom = (image.height + new_height) / 2
                image = image.crop((left, top, right, bottom))
            else:
                new_width, new_height = width, height

            image = image.resize((new_width, new_height), resample=self.resample_algorithm)

        if scale_percentage > 0:
            new_width = int(image.width * (scale_percentage / 100))
            new_height = int(image.height * (scale_percentage / 100))
            image = image.resize((new_width, new_height), resample=self.resample_algorithm)

        self.width, self.height = image.size

        return image


    def pixelize_image(self, image: Image, pixelize: int = 0) -> Image:
        """
        Pixelize the image by resizing it to a smaller size and then enlarging it back to the original size.
        The pixelize value determines the size of the smaller image.
        """
        if pixelize > 0:
            width, height = image.size
            aspect_ratio = width / height

            pixelize_width = pixelize
            pixelize_height = int(pixelize / aspect_ratio)

            # Leave resample algorithm NEAREST for pixelize
            small_image = image.resize((pixelize_width, pixelize_height), Image.NEAREST)
            image = small_image.resize(image.size, Image.NEAREST)

        return image

    def adjust_opacity(self, image: Image, alpha: float) -> Image:
        """Adjust the opacity of the image by changing the alpha channel."""
        np_image = np.array(image)

        if len(np_image.shape) == 3:
            if np_image.shape[2] == 4:
                np_image[..., 3] = (np_image[..., 3] * alpha).astype(np.uint8)
            else:
                np_image = np.dstack([np_image, np.full((np_image.shape[0], np_image.shape[1]), fill_value=int(255 * alpha), dtype=np.uint8)])

        image = Image.fromarray(np_image)
        return image
    
    def process_images(self):
        """Process all images in the source directory."""
        logging.info(f"Image source directory: {self.src_dir}")
        logging.info(f"Image destination directory: {self.dst_dir}\n")

        logging.info("Processing images...\n")

        if not os.path.exists(self.src_dir):
            logging.error("Image source directory does not exist.")
            raise FileNotFoundError(f"Image source directory {self.src_dir} does not exist.")

        progress_bar = tqdm(self.image_files, unit="image", desc="Processing")
        for i, file in enumerate(progress_bar, start=1):
            progress_bar.set_description(f"Processing {file.name}")
            with Image.open(file) as image:
                self.original_width, self.original_height = image.size
                self.width, self.height = image.size
                self.resize_algorithm = self.args.algo
                processed_image = image
                self.filename_addon = ""
                if self.args.scale or self.args.width != 0 or self.args.height != 0:
                    processed_image = self.crop_resize_image(image, self.args.width, self.args.height, self.args.scale)

                if self.args.blur_before > 0.0:
                    processed_image = self.image_blur(processed_image, self.args.blur_before)

                if self.args.halftone != "":
                    self.filename_addon += f"_halftone{self.args.htsample}"
                    if self.args.htsample != 10:
                        self.htsample = self.args.htsample

                    colors = self.get_color_values(self.args.halftone)
                    if len(colors) == 1:
                        foreground = colors[0]
                        background = "None"
                    else:
                        # Get the first and last colors.
                        foreground = colors[0]
                        background = colors[-1]

                    if background.lower() == "none":
                        background = None
                    
                    processed_image = self.create_halftone(processed_image, foreground, background)

                if self.args.dither:
                    self.filename_addon += "_dither"
                    processed_image = self.dither_image(processed_image)

                if self.args.halftone == "":
                    if self.args.reduce_colors > 0:
                        self.filename_addon += f"_{self.args.reduce_colors}color"
                        processed_image = self.quantize_image(processed_image, self.args.reduce_colors, self.args.set_colors)

                    if self.args.set_colors and self.args.reduce_colors == 0:
                        colors = self.get_color_values(self.args.set_colors)
                        self.args.reduce_colors = len(colors)
                        self.filename_addon += f"_{self.args.reduce_colors}color"
                        processed_image = self.quantize_image(processed_image, self.args.reduce_colors, self.args.set_colors)

                    if self.args.posterize > 0:
                        self.filename_addon += f"_posterize{self.args.posterize}"
                        processed_image = self.posterize_image(processed_image, self.args.posterize)

                    if self.args.pixelize:
                        self.filename_addon += f"_pixelized{self.args.pixelize}"
                        processed_image = self.pixelize_image(processed_image, self.args.pixelize)

                    if self.args.grayscale:
                        self.filename_addon += "_grayscale"
                        processed_image = self.convert_to_grayscale(processed_image)
                    
                    if self.args.brightness != 1.0:
                        self.filename_addon += f"_br{self.args.brightness}"
                        processed_image = self.adjust_brightness(processed_image, self.args.brightness)

                    if self.args.saturation != 1.0:
                        self.filename_addon += f"_sat{self.args.saturation}"
                        processed_image = self.adjust_saturation(processed_image, self.args.saturation)

                if self.args.set_trans_colors:
                    processed_image = self.transparent_colors(processed_image, self.args.set_trans_colors)

                if self.args.rotate != 0:
                    self.filename_addon += f"_rotated{self.args.rotate}"
                    processed_image =self.rotate_image(processed_image, self.args.rotate)

                if self.args.invert:
                    self.filename_addon += "_invert"
                    processed_image = self.invert_image(processed_image)
                
                if self.args.blur_after > 0.0:
                    processed_image = self.image_blur(processed_image, self.args.blur_after)

                if self.args.opacity >= 0.0 and self.args.opacity < 1.0:
                    self.filename_addon += f"_opacity{self.args.opacity}"
                    processed_image = self.adjust_opacity(processed_image, self.args.opacity)

                new_filename = f"{file.stem}_{self.width}x{self.height}{self.filename_addon}"

                if self.args.filetype:
                    dst_file = os.path.join(self.dst_dir, new_filename + self.args.filetype.lower())
                else:
                    dst_file = os.path.join(self.dst_dir, new_filename + file.suffix)

                if self.args.filetype and self.args.filetype.lower() == ".jpg":
                    processed_image.convert("RGB").save(dst_file, format='JPEG')
                else:
                    processed_image.save(dst_file)

                progress_bar.set_description(f"Processed {file.name}")
                progress_bar.update()

        progress_bar.close()

        logging.info("\nBatch processing completed.")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process images.')
    parser.add_argument('-s', '--src_dir', default='src', help='Source (src) directory (contains original images to be processed)')
    parser.add_argument('-d', '--dst_dir', default='dst', help='Destination (dst) directory (contains newly created images)')
    parser.add_argument('-c', '--reduce_colors', type=int, default=0, help='Reduce the amount of colors in the images color palette')
    parser.add_argument('-g', '--grayscale', action='store_true', default=False, help='Grayscale')
    parser.add_argument('-i', '--invert', action='store_true', help='Invert colors')
    parser.add_argument('-o', '--opacity', type=float, default=1.0, help='Set opacity of final image (values 0.0 to 1.0 with zero being fully transparent)')
    parser.add_argument('-r', '--rotate', type=int, default=0, help='Rotation angle')
    parser.add_argument('--width', type=int, default=0, help='New width')
    parser.add_argument('--height', type=int, default=0, help='New height')
    parser.add_argument('--scale', type=int, default=0, help='Scale percentage')
    parser.add_argument('--algo', type=int, default=1, help='Change resample algorithm NEAREST = 0, LANCZOS = 1, BILINEAR = 2, BICUBIC = 3, BOX = 4, HAMMING = 5')
    parser.add_argument('--filetype', default='.png', help='Output filetype - .png (preserve transparency effects) or .jpg (no transparency, generally smaller file sizes)')
    parser.add_argument('--pixelize', type=int, nargs='?', const=None, default=0, help='Pixelize')
    parser.add_argument('--halftone', nargs='?', const=None, default='', help='Halftone foreground and background colors')
    parser.add_argument('--dither', action='store_true', default=False, help='Apply FLOYDSTEINBERG dithering')
    parser.add_argument('--posterize', type=int, nargs='?', const=None, default=0, help='Posterize image bits 1-8')
    parser.add_argument('--blur_before', type=float, default=0.0, help='Blur factor (before any effects applied) - Recommended values 0-10, high values can be used')
    parser.add_argument('--blur_after', type=float, default=0.0, help='Blur factor (after any effects are applied) - Recommended values 0-10, high values can be used')
    parser.add_argument('--brightness', type=float, default=1.0, help='Brightness', dest='brightness')
    parser.add_argument('--saturation', type=float, default=1.0, help='Saturation', dest='saturation')
    parser.add_argument('--htsample', type=int, default=10, help='Change halftone sample size')
    parser.add_argument('--shuffle_colors', action='store_true', default=True, help='Colors in --set_colors including color palettes will be shuffled each time.')
    parser.add_argument('--set_colors', default='', help='Custom colors or color palette name to replace existing colors')
    parser.add_argument('--set_trans_colors', default='', help='Colors to be made transparent')

    args = parser.parse_args()

    if len(sys.argv) > 1:
        if args.halftone is None:
            args.halftone = '#000000,#FFFFFF'

        # If posterize is used without any argument
        if args.posterize is None:
            args.posterize = 1

        # If posterize is used without any argument
        if args.pixelize is None:
            args.pixelize = 128

        return args
    else:
        print("No command line arguments provided")
        parser.print_help()
        sys.exit(1)

def banner():
    print(f'''

 ██████╗ ██╗██╗     ███████╗██╗  ██╗
 ██╔══██╗██║██║     ██╔════╝╚██╗██╔╝
 ██████╔╝██║██║     █████╗   ╚███╔╝ 
 ██╔═══╝ ██║██║     ██╔══╝   ██╔██╗ 
 ██║     ██║███████╗██║     ██╔╝ ██╗
 ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝

 [Batch Image Transformations and Effects with Python PIL]
''')


def main():
    banner()

    args = parse_arguments()
    batch = BatchPILFX(args)
    batch.process_images()


if __name__ == "__main__":
    main()
