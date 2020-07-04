#import arxiv
import feedparser
import arxiv
import pickle
from os.path import isfile, join
from os import chdir, makedirs

from subprocess import call

rss_url = "http://export.arxiv.org/rss/"

subject_string = "math" #"physics.ao-ph"

template_str = """
\\documentclass[preview, border=10pt]{{standalone}}
\\usepackage{{amsfonts, setspace, amsmath, amsthm,mathrsfs, amssymb, graphicx, tikz}}
\\usepackage{{fontspec}}
\\setmainfont{{CMU Serif}}


\\begin{{document}}

\section*{{ {title_string} }}

\subsection*{{ {author_string} }}

{summary_string}
\\\\
\\\\
{subject_string}


\\end{{document}}"""

verb_template_str = """
\\documentclass[preview, border=10pt]{{standalone}}
\\usepackage{{amsfonts, setspace, amsmath, amsthm,mathrsfs, amssymb, graphicx, tikz}}
\\usepackage{{fontspec}}
\\usepackage{{spverbatim}}
\\setmainfont{{CMU Serif}}

\\begin{{document}}

\\begin{{spverbatim}} 
Title: 
{title_string}

Author: 
{author_string}

Summary:
{summary_string}


\\end{{spverbatim}}
{subject_string}

\\end{{document}}"""


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
    return idx.split("/")[-1]

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

def clean_image_files(item):
    main_subject = item['arxiv_primary_category']['term']

def generate_image(item):
    idx = strip_id(item["id"])
    path = join(root_directory, tex_dir, idx)
    fname = idx + ".tex"
    fpath = join(path, fname)
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
    
    if call(["xelatex", "-interaction=batchmode", idx + ".tex"]) != 0:
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
        
        res = call(["xelatex", "-interaction=batchmode", idx + ".tex"])
        log_lines(["Compilation error for id {}:".format(idx),
                   "\t Sanitized compilation exited with status {}".format(res)])
        if res != 0:

            tex_string = verb_template_str.format(title_string=title_string.replace("\n", " "),
                                    author_string=author_string.replace("\n", " "),
                                    subject_string=subject_string.replace("\n", " "),
                                    summary_string=summary_string.replace("\n", " "))
            with open(fname, "w") as f:
                f.write(tex_string)
            res = call(["xelatex", "-interaction=batchmode", idx + ".tex"])
            log_lines(["\t Verbatim compilation exited with status {}".format(res)])

    chdir(root_directory)
    archive_tex(idx, tex_string)
    call(['convert', '-density', '600', join(path, idx + ".pdf"), join(image_dir, idx + ".png")])

def clean_image_files(item):
    main_subject = item['arxiv_primary_category']['term']
    # TODO: implement this

def check_if_published(idx):
    try:
        with open(join(root_directory, arxiv_file), "rb") as f:
            strings = pickle.load(f)
        return idx in strings
    except OSError as e:
        return False


def register_published(id):
    fpath = join(root_directory, arxiv_file)
    try:
        with open(fpath, "rb") as f:
            strings = pickle.load(f)
        strings.append(id)
        with open(fpath, "wb") as f:
            pickle.dump(strings, f)
    except OSError as e:
        if not isfile(fpath):
            with open(fpath, "wb") as f:
                pickle.dump([id], f)
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

def get_feed_list(subject):
    feed = feedparser.parse(rss_url + subject_string)
    ids = [strip_id(item['id']) for item in feed['items']]
    ids_filt = [x for x in filter(lambda idx: not check_if_published(idx), ids)]
    results = parse_feed_list(arxiv.query(id_list=ids_filt))
    [generate_image(item) for item in results]

    print(len(results))


    




def publish(feed_item):
    pass





if __name__ == "__main__":
    dirs = [image_dir, tex_dir]
    [makedirs(join(root_directory, dr), exist_ok=True) for dr in dirs]
    get_feed_list(subject_string)