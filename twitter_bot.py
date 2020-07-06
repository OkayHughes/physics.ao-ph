#import arxiv
import feedparser
import arxiv
import pickle
import tweepy
import fitz
import psycopg2
from templates import template_str, verb_template_str
from os.path import isfile, join
from os import chdir, makedirs, remove, environ, getcwd
from shutil import rmtree
from time import sleep


consumer_key = environ["CONSUMER_KEY"]
consumer_key_secret = environ["CONSUMER_KEY_SECRET"]
access_token = environ["ACCESS_TOKEN"]
access_token_secret = environ["ACCESS_TOKEN_SECRET"]

rss_url = "http://export.arxiv.org/rss/"

subject_string = "physics.ao-ph"


log_file = "log.txt"
arxiv_file = "id_archive.pkl"
image_dir = "images/"
pdf_dir = "pdf/"

root_directory = "/app"

DATABASE_URL = environ['DATABASE_URL']
table_name = "idxs"
column_name = "idx"



# Read recent papers
# Compare against list of preexisting 


def get_database_url():
    return DATABASE_URL

def initialize_DB():
    conn = psycopg2.connect(get_database_url())
    return conn

def create_table():
    conn = initialize_DB()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pg_catalog.pg_tables WHERE tablename='{}';".format(table_name))
    if len(cur.fetchall()) == 0:
        cur.execute("CREATE TABLE {} (id serial PRIMARY KEY, {} varchar);".format(table_name, column_name))
    cur.close()
    conn.commit()
    conn.close()

def drop_table():
    conn = initialize_DB()
    cur = conn.cursor()
    cur.execute("DROP TABLE {};".format(table_name))
    cur.close()
    conn.commit()
    conn.close()

def check_if_published(idx, conn):
    conn = initialize_DB()
    cur = conn.cursor()
    query = "SELECT * FROM {} WHERE {}='{}';".format(table_name, column_name, idx)
    cur.execute(query)
    val = len(cur.fetchall()) > 0
    if val > 1:
        log_lines(["Id {} appears to have duplicate publications".format(idx)])
    cur.close()
    return val


def register_published(idx, conn):
    conn = initialize_DB()
    cur = conn.cursor()
    query = "INSERT INTO {} ({}) VALUES ('{}');".format(table_name, column_name, idx)
    cur.execute(query)
    cur.close()
    conn.commit()

def log_lines(lines):
    print("\n".join(lines))



def strip_id(idx):
    idx = idx.split("/")[-1]
    return idx

def get_id(item):
    return strip_id(item['id'])

def parse_feed_list(feed_list):
    ret_list = [{} for _ in feed_list]
    for i, item in enumerate(feed_list):
        keys = ["authors", "id", "title", "tags", "arxiv_primary_category", "summary", "pdf_url"]
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

def get_pdf_path(item):
    idx = strip_id(item["id"])
    path = join(root_directory, pdf_dir, idx)
    pdfname = idx + ".pdf"
    fpath = join(path, pdfname)
    return path, pdfname, fpath

def get_image_path(item):
    idx = get_id(item)
    path = join(root_directory, image_dir)
    fname = idx + ".png"
    fpath = join(path, fname)
    return path, fname, fpath

def clean_image_files(item):
    path, _, _ = get_pdf_path(item)
    idx = get_id(item)
    try:
        rmtree(path)
    except:
        log_lines(["Error removing pdf files for id {}".format(idx)])
    path, fname, fpath = get_image_path(item)
    try:
        remove(fpath)
    except:
        log_lines(["Error removing img files for id {}".format(idx)])




def generate_image(item):
    path, fname, fpath = get_pdf_path(item)
    img_path, img_fname, img_fpath = get_image_path(item)
    _, _, img_path = get_image_path(item)
    doc = fitz.open(fpath)
    page = doc.loadPage(0)
    mat = fitz.Matrix(2, 2)
    pix = page.getPixmap(matrix = mat)
    pix.writeImage(img_fpath)
    

def initialize_tweepy_api():
    auth = tweepy.OAuthHandler(consumer_key, consumer_key_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    return api



def publish(feed_item, api):
    _, _, image_path = get_image_path(feed_item)
    tweet_text = format_tweet_string(feed_item)
    log_lines(["TWEET PUBLISHED: {}".format(strip_id(feed_item['id']))])
    status = api.update_with_media(image_path, tweet_text)

def download_pdf(item):
    path, fname, fpath = get_pdf_path(item)
    makedirs(path, exist_ok=True)
    arxiv.download(item, dirpath = path, slugify=lambda paper: ".".join(fname.split(".")[:-1]))

def main_loop(subject):
    feed = feedparser.parse(rss_url + subject_string)
    ids = [strip_id(item['id']) for item in feed['items']]
    items = parse_feed_list(arxiv.query(id_list=ids))
    ids = [strip_id(item['id']) for item in items]
    
    conn = initialize_DB()
    items = [x[0] for x in filter(lambda pair: not check_if_published(pair[1], conn), zip(items, ids))]
    ids = [x for x in filter(lambda idx: not check_if_published(idx, conn), ids)]
    conn.close()
    [download_pdf(item) for item in items]
    [generate_image(item) for item in items]

    conn = initialize_DB()
    api = initialize_tweepy_api()
    for (idx, item) in zip(ids, items):
        publish(item, api)
        register_published(idx, conn)
        sleep(2)

    conn.close()
    [clean_image_files(item) for item in items]





if __name__ == "__main__":
    create_table()
    dirs = [image_dir, pdf_dir]
    [makedirs(join(root_directory, dr), exist_ok=True) for dr in dirs]
    main_loop(subject_string)