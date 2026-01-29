import sys, re
def resolve_markdown_list(content):
    pattern = re.compile(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>>', re.DOTALL)
    def replacement(match):
        combined = list(dict.fromkeys(match.group(1).split('\n') + match.group(2).split('\n')))
        return '\n'.join(combined)
    return pattern.sub(replacement, content)
if __name__ == "__main__":
    with open(sys.argv[1], 'r+') as f:
        c = f.read(); f.seek(0); f.write(resolve_markdown_list(c)); f.truncate()
