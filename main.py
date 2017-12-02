import json
import urllib
import os
from PIL import Image

api_base_path = "https://hoffnung3000-gif-stream.herokuapp.com"


def fetch(marker=""):
    json_response = json.load(
        urllib.urlopen(api_base_path + "/api/stream?marker=" + marker))
    return json_response["nextMarker"], json_response["data"]


def fetch_all():
    next_marker = ""
    gif_urls = []

    while True:
        next_marker, gif_data = fetch(next_marker)
        gif_urls = gif_urls + [item["url"] for item in gif_data]
        if not next_marker:
            break

    return gif_urls


def download_gif_file(url):
    if not os.path.exists("gifs"):
        os.makedirs("gifs")

    file_name = url.split("/")[-1]
    print "Download '{}'".format(file_name)
    urllib.urlretrieve(url, "gifs/" + file_name)


def download_all_gif_files():
    print "Fetch .gif URLs from server ..."
    gif_urls = fetch_all()
    print "Found {} .gif URLs.".format(len(gif_urls))
    print ""
    for url in gif_urls:
        download_gif_file(url)
    print "Downloads finished."


# From https://gist.github.com/BigglesZX/4016539
def analyse_image(path):
    '''
    Pre-process pass over the image to determine the mode (full or additive).
    Necessary as assessing single frames isn't reliable. Need to know the mode
    before processing all frames.
    '''
    im = Image.open(path)
    results = {
        "size": im.size,
        "mode": "full",
    }
    try:
        while True:
            if im.tile:
                tile = im.tile[0]
                update_region = tile[1]
                update_region_dimensions = update_region[2:]
                if update_region_dimensions != im.size:
                    results["mode"] = "partial"
                    break
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return results


def process_image(path):
    '''
    Iterate the GIF, extracting each frame.
    '''
    mode = analyse_image(path)["mode"]

    im = Image.open(path)

    i = 0
    p = im.getpalette()
    last_frame = im.convert("RGBA")

    try:
        while True:
            print "saving %s (%s) frame %d, %s %s" % (path, mode, i, im.size, im.tile)

            '''
            If the GIF uses local colour tables, each frame will have its
            own palette. If not, we need to apply the global palette to
            the new frame.
            '''
            if not im.getpalette():
                im.putpalette(p)

            new_frame = Image.new('RGBA', im.size)

            '''
            Is this file a "partial"-mode GIF where frames
            update a region of a different size to the entire image?
            If so, we need to construct the new frame by pasting it on
            top of the preceding frames.
            '''
            if mode == "partial":
                new_frame.paste(last_frame)

            new_frame.paste(im, (0,0), im.convert("RGBA"))
            new_frame.save(
              "frames/%s-%d.png" % (
                "".join(os.path.basename(path).split(".")[:-1]), i), "PNG")

            i += 1
            last_frame = new_frame
            im.seek(im.tell() + 1)
    except EOFError:
        pass


def extract_frames():
    if not os.path.exists("gifs"):
        print "Error: Can't find 'gifs' folder."
        exit()

    if not os.path.exists("frames"):
        os.makedirs("frames")

    files = [f for f in os.listdir("gifs") if os.path.isfile(
        os.path.join("gifs", f))]

    for file in files:
        process_image("gifs/" + file)


def make_grid(tile_size=100, image_width=3200, image_height=4900):
    if not os.path.exists("frames"):
        print "Error: Can't find 'frames' folder."
        exit()

    if not os.path.exists("pages"):
        os.makedirs("pages")

    files = [f for f in os.listdir("frames") if os.path.isfile(
        os.path.join("frames", f))]
    files.sort()

    page_image = Image.new("RGB", (image_width, image_height))
    file_index_start = 0
    file_index = 0
    page_index = 0

    while (file_index < len(files)):
        for i in xrange(0, image_width + 1, tile_size):
            for j in xrange(0, image_height + 1, tile_size):
                if file_index > len(files) - 1:
                    break
                file = files[file_index]
                tile_image = Image.open("frames/" + file)
                tile_image.thumbnail((tile_size, tile_size))
                page_image.paste(tile_image, (i, j))
                file_index += 1

        page_path = "pages/page-{}.jpg".format(page_index + 1)
        print "Draw frames {}-{} into page '{}'".format(
            file_index_start, file_index, page_path)
        page_image.save(page_path, "JPEG", quality=100)
        page_index += 1
        file_index_start = file_index


if __name__ == "__main__":
    download_all_gif_files()
    extract_frames()
    make_grid()
