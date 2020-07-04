import subprocess
import sys


packages = ["arxiv",
            "feedparser",
            "python-twitter",
            "tweepy"]
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])



if __name__ == "__main__":
    for package in packages:
        install(package)

