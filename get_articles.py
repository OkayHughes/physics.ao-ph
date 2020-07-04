#import arxiv
import feedparser
import arxiv
import pickle
import tweepy
from secrets import consumer_key, consumer_key_secret
from secrets import access_token, access_token_secret
from templates import template_str, verb_template_str
from os.path import isfile, join
from os import chdir, makedirs, remove
from shutil import rmtree
from time import sleep
from subprocess import call

rss_url = "http://export.arxiv.org/rss/"

subject_string = "physics.ao-ph"


log_file = "log.txt"
arxiv_file = "id_archive.pkl"
tex_archive_file = "tex_archive.pkl"
image_dir = "images/"
tex_dir = "tex/"

root_directory = "/Users/OstensiblyOwen/development/python/twitter_bot"



# Read recent papers
# Compare against list of preexisting 


def log_lines(lines):
    fpath = join(root_directory, log_file)
    try:
        with open(fpath, "a") as f:
            f.write("\n".join(lines) + "\n")
    except OSError as e:
        if not isfile(fpath):
            with open(fpath, "w") as f:
                f.write("\n".join(lines) + "\n")
        else:
            log_lines(["Error Logged:", str(e)])



def strip_id(idx):
    idx = idx.split("/")[-1]
    return idx

def parse_feed_list(feed_list):
    ret_list = [{} for _ in feed_list]
    for i, item in enumerate(feed_list):
        keys = ["authors", "id", "title", "tags", "arxiv_primary_category", "summary"]
        for key in keys:
            ret_list[i][key] = item[key]
    return ret_list


def gen_title_string(item):
    return item["title"]

def gen_summary_string(item):
    return item["summary"]

def gen_author_string(item):
    authors = item["authors"]
    if len(authors) > 3:
        return authors[0] + " et al."
    elif len(authors) == 3:
        return authors[0] + ", " +  authors[1] + ", and " + authors[2]
    else:
        return " and ".join(authors)

def gen_subject_string(item):
    main_subject = item['arxiv_primary_category']['term']
    secondary_subjects = [tag['term'] for tag in item['tags']]
    if len(secondary_subjects) == 1:
        ret_string = "Subject Area: "
    else:
        ret_string = "Subject Areas: "
    ret_string += "\\textbf{{{main_subject}}}".format(main_subject=main_subject)
    for subject in secondary_subjects:
        if subject != main_subject:
            ret_string += ", " + subject
    return ret_string


def format_tweet_string(item):
    lines = []
    lines.append(item['id'])
    lines.append(gen_title_string(item))
    lines.append(gen_author_string(item))
    return "\n\n".join(lines)

def get_tex_path(item):
    idx = strip_id(item["id"])
    path = join(root_directory, tex_dir, idx)
    texname = idx + ".tex"
    pdfname = idx + ".pdf"
    fpath = join(path, texname)
    return path, texname, pdfname, fpath

def get_image_path(item):
    idx = strip_id(item["id"])
    path = join(root_directory, image_dir)
    fname = idx + ".jpg"
    fpath = join(path, fname)
    return path, fname, fpath

def clean_image_files(item):
    path, _, _, _ = get_tex_path(item)
    try:
        rmtree(path)
    except:
        log_lines(["Error removing tex files for id {}".format(dx)])
    path, fname, fpath = get_image_path(item)
    try:
        remove(fpath)
    except:
        log_lines(["Error removing img files for id {}".format(dx)])




def generate_image(item):

    path, fname, pdfname, fpath = get_tex_path(item)
    _, _, img_path = get_image_path(item)
    makedirs(path, exist_ok=True)
    title_string = gen_title_string(item)
    summary_string = gen_summary_string(item)
    author_string = gen_author_string(item)
    subject_string = gen_subject_string(item)

    tex_string = template_str.format(title_string=title_string,
                                    author_string=author_string,
                                    subject_string=subject_string,
                                    summary_string=summary_string)
    chdir(path)
    with open(fname, "w") as f:
        f.write(tex_string)
    
    if call(["xelatex", "-interaction=batchmode", fname]) != 0:
        escape_func = lambda x : x.translate(str.maketrans({"$":  r"\$",
                                        "_":  r"\textunderscore ",
                                        "^":  r"\^{}",
                                        "#":  r"\#",
                                        "{":  r"\{",
                                        "}":  r"\}",
                                        "%":  r"\%",
                                        "&":  r"\&",
                                        "~":  r"\textasciitilde ",
                                          "\\":  r"\textbackslash "}))
        title_string_new = escape_func(title_string)

        summary_string_new = escape_func(summary_string)
        author_string_new = escape_func(author_string)

        tex_string = template_str.format(title_string=title_string_new,
                                    author_string=author_string_new,
                                    subject_string=subject_string,
                                    summary_string=summary_string_new)
        with open(fname, "w") as f:
            f.write(tex_string)
        
        res = call(["xelatex", "-interaction=batchmode", fname])
        log_lines(["Compilation error for id {}:".format(fname),
                   "\t Sanitized compilation exited with status {}".format(res)])
        if res != 0:

            tex_string = verb_template_str.format(title_string=title_string.replace("\n", " "),
                                    author_string=author_string.replace("\n", " "),
                                    subject_string=subject_string.replace("\n", " "),
                                    summary_string=summary_string.replace("\n", " "))
            with open(fname, "w") as f:
                f.write(tex_string)
            res = call(["xelatex", "-interaction=batchmode", fname])
            log_lines(["\t Verbatim compilation exited with status {}".format(res)])

    chdir(root_directory)
    archive_tex(fname, tex_string)
    call(['convert', '-density', '600', "-background", "white", join(path, pdfname), img_path])



def check_if_published(idx):
    try:
        with open(join(root_directory, arxiv_file), "rb") as f:
            strings = pickle.load(f)
        return idx in strings
    except OSError as e:
        return False


def register_published(idx):
    fpath = join(root_directory, arxiv_file)
    try:
        with open(fpath, "rb") as f:
            strings = pickle.load(f)
        strings.append(idx)
        with open(fpath, "wb") as f:
            pickle.dump(strings, f)
    except OSError as e:
        if not isfile(fpath):
            with open(fpath, "wb") as f:
                pickle.dump([idx], f)
        else:
            log_lines(["Error Logged for id {}:".format(idx), str(e)])

def archive_tex(idx, string):
    fpath = join(root_directory, tex_archive_file)
    try:
        with open(fpath, "rb") as f:
            strings = pickle.load(f)
        if idx not in strings.keys():
            strings[idx] = string
            with open(fpath, "wb") as f:
                pickle.dump(strings, f)
    except OSError as e:
        if not isfile(fpath):
            with open(fpath, "wb") as f:
                pickle.dump({idx : string}, f)
        else:
            log_lines(["Error Logged for id {}:".format(idx), str(e)])


def initialize_tweepy_api():
    auth = tweepy.OAuthHandler(consumer_key, consumer_key_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    return api



def publish(feed_item, api):
    _, _, fpath = get_image_path(feed_item)
    tweet_text = format_tweet_string(feed_item)
    image_path = fpath
    status = api.update_with_media(image_path, tweet_text)

def main_loop(subject):
    feed = feedparser.parse(rss_url + subject_string)
    ids = [strip_id(item['id']) for item in feed['items']]
    items = parse_feed_list(arxiv.query(id_list=ids))
    ids = [strip_id(item['id']) for item in items]
    items = [x[0] for x in filter(lambda pair: not check_if_published(pair[1]), zip(items, ids))]
    ids = [x for x in filter(lambda idx: not check_if_published(idx), ids)]


    [generate_image(item) for item in items]
    api = initialize_tweepy_api()
    for (idx, item) in zip(ids, items):
        publish(item, api)
        register_published(idx)
        sleep(2)

    [clean_image_files(item) for item in items]


if __name__ == "__main__":
    dirs = [image_dir, tex_dir]
    [makedirs(join(root_directory, dr), exist_ok=True) for dr in dirs]
    main_loop(subject_string)