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