#!/usr/bin/env python3
import os
import shutil
import traceback
from itertools import permutations
from random import choice
from sys import argv

import imagehash
import numpy as np
import requests as req
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By

# from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options
from tqdm.auto import tqdm

columns = shutil.get_terminal_size().columns


uagent = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 12_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/79.0.3945.73 Mobile/15E148 Safari/605.1",
    "Mozilla/5.0 (Linux; Android 8.0.0;) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.136 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36",  ##
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/72.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) Gecko/20100101 Firefox/72.0",
    "Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/72.0",
    "Mozilla/5.0 (Android 8.0.0; Mobile; rv:61.0) Gecko/61.0 Firefox/68.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 12_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/21.0 Mobile/16B92 Safari/605.1.15",
]
mobile_emulation = {"deviceName": "Nexus 10"}


class Pints:
    def __init__(self, search, amount, headless=True):
        self.opt = Options()
        # self.opt.add_experimental_option('mobileEmulation',mobile_emulation)
        self.opt.add_argument("--incognito")
        if headless:
            self.opt.add_argument("--headless")
        self.opt.add_argument("--disable-gpu")
        # self.opt.add_experimental_option('excludeSwitches', ['enable-logging'])
        self.search = search
        self.original_amount = amount
        self.amount = amount * 2

        self.loc = "drivers/geckodriver"
        self.link = "https://id.pinterest.com/search/pins/?q=%s&rs=typed" % (
            self.search
        )
        self.alf = webdriver.Firefox(executable_path=self.loc, options=self.opt)
        self.alf.get(self.link)

        self.result_dir = os.path.join("./", "result")
        self.search_dir = os.path.join(self.result_dir, self.search)

    def scan(self, retry=False):
        image_links = []
        index = 1

        while index <= self.amount:
            elements_found = self.alf.find_elements(By.TAG_NAME, "img")

            for element in elements_found:

                try:
                    element_attribute = element.get_attribute("src")

                except Exception:
                    print(traceback.format_exc())
                    print("\n\n")
                else:

                    if "75x75_RS" in element_attribute:
                        image_url = element_attribute.replace("75x75_RS", "originals")
                    else:
                        image_url = element_attribute.replace("236x", "originals")

                    image_name = image_url.split("/")[-1]
                    print(f"{index}/{self.amount} : {image_name}")

                    index += 1

                    # self.alf.switch_to.window(self.alf.window_handles[1])

                    if image_url not in image_links:
                        # if 'i.pinimg.com' not in req.get(k).text:
                        #     k = k.replace('jpg','png')
                        #     if 'i.pinimg.com' not in req.get(k).text:
                        #         k = k.replace('png','gif')

                        image_links.append(image_url)

                    if len(image_links) >= self.amount:
                        break

            if len(image_links) >= self.amount:
                print("\n")
                break
            else:
                self.alf.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
        return image_links

    def save(self, urls):

        os.makedirs(self.search_dir, exist_ok=True)

        tasks = tqdm(range(len(urls)), desc="Downloading images", unit_scale=True)

        for index in tasks:
            image_url = urls[index]
            image_content = req.get(
                image_url, headers={"User-Agent": choice(uagent)}
            ).content
            rename = image_url.split("/")[-1:][0]
            image_filename = os.path.join(self.search_dir, rename)

            if os.path.exists(image_filename):
                continue
            else:
                with open(image_filename, "wb") as image_file_obj:
                    image_file_obj.write(image_content)
                    image_file_obj.close()

                try:
                    image_obj = Image.open(image_filename)
                    image_obj.verify()
                except (IOError, SyntaxError) as e:
                    os.remove(image_filename)

        self.check_total_images()

    def check_total_images(self):

        downloaded_images = os.listdir(self.search_dir)

        if len(downloaded_images) < self.original_amount:
            print(f"We could find only {len(downloaded_images)} good images.\n\n")
            new_images = self.scan(retry=True)
            self.save(new_images)
            remove_duplicates(self.search_dir)

        else:
            print(f"All images are in!!!")


def get_duplicate_images(images_path):

    duplicates = set()

    found_images = os.listdir(images_path)
    permutes = permutations(found_images, 2)

    image_hash = with_ztransform_preprocess(imagehash.dhash, hash_size=8)
    hashes = {}

    for image_path in found_images:
        if image_path not in hashes:
            hashes[image_hash] = ""
            hashes[image_path] = image_hash(os.path.join(images_path, image_path))
        else:
            hashes[image_path] = image_hash(os.path.join(images_path, image_path))

    for permute in permutes:
        left_image = permute[0]
        right_image = permute[1]

        left_hash = hashes[left_image]
        right_hash = hashes[right_image]

        if left_hash == right_hash:
            print(f"Images '{permute}' are similar.")
            duplicates.add(left_image)

    return duplicates


def remove_duplicates(path):
    duplicates = get_duplicate_images(path)

    for duplicate in duplicates:
        os.remove(os.path.join(path, duplicate))
    return duplicates


def alpharemover(image):
    if image.mode != "RGBA":
        return image
    canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
    canvas.paste(image, mask=image)
    return canvas.convert("RGB")


def with_ztransform_preprocess(hashfunc, hash_size=8):
    def function(path):
        image = alpharemover(Image.open(path))
        image = image.convert("L").resize(
            (hash_size, hash_size), Image.Resampling.LANCZOS
        )
        data = image.getdata()
        quantiles = np.arange(100)
        quantiles_values = np.percentile(data, quantiles)
        zdata = (np.interp(data, quantiles_values, quantiles) / 100 * 255).astype(
            np.uint8
        )
        image.putdata(zdata)
        return hashfunc(image)

    return function


def start():
    os.system("cls")
    print()
    print("| [github.com/algatra] - pinterest scraper |".center(columns, "-"))
    search = str(input("-> Search For : "))
    amount = int(input("   -> Amount : "))
    print("| Scanning . . . |".center(columns, "-"))

    try:
        if "false" in str(argv).lower():
            run = Pints(search, amount, False)
        else:
            run = Pints(search, amount)
    except:
        print(traceback.format_exc())
        exit()

    pas = run.scan()
    print("| Downloading . . . |".center(columns, "-"))
    run.save(pas)
    run.alf.quit()

    print("| Done ! |".center(columns, "-"))


if __name__ == "__main__":
    start()