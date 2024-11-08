#!/usr/bin/python3

import asyncio
import os
import re

import aiohttp
import json

from github_stats import Stats


################################################################################
# Helper Functions
################################################################################


def generate_output_folder() -> None:
    """
    Create the output folder if it does not already exist
    """
    if not os.path.isdir("generated"):
        os.mkdir("generated")


################################################################################
# Individual Image Generation Functions
################################################################################


async def generate_overview(s: Stats) -> None:
    """
    Generate a JSON file with summary statistics and an SVG badge
    :param s: Represents user's GitHub statistics
    """
    # Gather data for JSON
    overview_data = {
        "name": await s.name,
        "stars": await s.stargazers,
        "forks": await s.forks,
        "contributions": await s.total_contributions,
        "lines_changed": (await s.lines_changed)[0] + (await s.lines_changed)[1],
        "views": await s.views,
        "repos": len(await s.repos)
    }

    # Write JSON file
    generate_output_folder()
    with open("generated/overview.json", "w") as f:
        json.dump(overview_data, f, indent=4)

    # Generate SVG
    with open("templates/overview.svg", "r") as f:
        output = f.read()

    output = re.sub("{{ name }}", overview_data["name"], output)
    output = re.sub("{{ stars }}", f"{overview_data['stars']:,}", output)
    output = re.sub("{{ forks }}", f"{overview_data['forks']:,}", output)
    output = re.sub("{{ contributions }}", f"{overview_data['contributions']:,}", output)
    output = re.sub("{{ lines_changed }}", f"{overview_data['lines_changed']:,}", output)
    output = re.sub("{{ views }}", f"{overview_data['views']:,}", output)
    output = re.sub("{{ repos }}", f"{overview_data['repos']:,}", output)

    with open("generated/overview.svg", "w") as f:
        f.write(output)


async def generate_languages(s: Stats) -> None:
    """
    Generate a JSON file with summary languages used and an SVG badge
    :param s: Represents user's GitHub statistics
    """
    # Gather and sort language data for JSON
    sorted_languages = sorted(
        (await s.languages).items(), reverse=True, key=lambda t: t[1].get("size")
    )

    languages_data = {
        lang: {
            "size": data.get("size"),
            "color": data.get("color"),
            "percentage": data.get("prop", 0)
        }
        for lang, data in sorted_languages
    }

    # Write JSON file
    generate_output_folder()
    with open("generated/languages.json", "w") as f:
        json.dump(languages_data, f, indent=4)

    # Generate SVG
    with open("templates/languages.svg", "r") as f:
        output = f.read()

    progress = ""
    lang_list = ""
    delay_between = 150
    for i, (lang, data) in enumerate(sorted_languages):
        color = data.get("color", "#000000")
        progress += (
            f'<span style="background-color: {color};'
            f'width: {data.get("prop", 0):0.3f}%;" '
            f'class="progress-item"></span>'
        )
        lang_list += f"""
<li style="animation-delay: {i * delay_between}ms;">
<svg xmlns="http://www.w3.org/2000/svg" class="octicon" style="fill:{color};"
viewBox="0 0 16 16" version="1.1" width="16" height="16"><path
fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8z"></path></svg>
<span class="lang">{lang}</span>
<span class="percent">{data.get("prop", 0):0.2f}%</span>
</li>
"""

    output = re.sub(r"{{ progress }}", progress, output)
    output = re.sub(r"{{ lang_list }}", lang_list, output)

    with open("generated/languages.svg", "w") as f:
        f.write(output)


################################################################################
# Main Function
################################################################################


async def main() -> None:
    """
    Generate all badges
    """
    access_token = os.getenv("ACCESS_TOKEN")
    if not access_token:
        # access_token = os.getenv("GITHUB_TOKEN")
        raise Exception("A personal access token is required to proceed!")
    user = os.getenv("GITHUB_ACTOR")
    if user is None:
        raise RuntimeError("Environment variable GITHUB_ACTOR must be set.")
    exclude_repos = os.getenv("EXCLUDED")
    excluded_repos = (
        {x.strip() for x in exclude_repos.split(",")} if exclude_repos else None
    )
    exclude_langs = os.getenv("EXCLUDED_LANGS")
    excluded_langs = (
        {x.strip() for x in exclude_langs.split(",")} if exclude_langs else None
    )
    # Convert a truthy value to a Boolean
    raw_ignore_forked_repos = "true"
    ignore_forked_repos = (
        not not raw_ignore_forked_repos
        and raw_ignore_forked_repos.strip().lower() != "false"
    )
    async with aiohttp.ClientSession() as session:
        s = Stats(
            user,
            access_token,
            session,
            exclude_repos=excluded_repos,
            exclude_langs=excluded_langs,
            ignore_forked_repos=ignore_forked_repos,
        )
        await asyncio.gather(generate_languages(s), generate_overview(s))


if __name__ == "__main__":
    asyncio.run(main())
