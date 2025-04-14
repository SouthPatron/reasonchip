#!/usr/bin/env python

import os
import argparse
import importlib
import textwrap
import datetime

from jinja2 import Environment
import markdown

from collections import defaultdict

from reasonchip.core.engine.registry import Registry, RegistryLoader


def markdown_to_html(value):
    if not value:
        return ""
    return markdown.markdown(
        textwrap.dedent(value),
        extensions=['extra'],
    )


def generate_module_docs(
    output_dir: str,
    chip_template: str,
):
    """
    Generate a single documentation file per module, grouping all chips
    in that module.
    """
    # Template
    env = Environment()
    env.filters["markdown"] = markdown_to_html
    tmpl = env.from_string(chip_template)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Load chips into registry
    RegistryLoader.load_module_tree("reasonchip.chipsets")
    chips = Registry.registry()

    # Group chips by module
    modules = defaultdict(list)
    for chip_name, entry in chips.items():
        remove_str = "reasonchip.chipsets."
        chip_name = chip_name.replace(remove_str, "")
        modules[entry.func.__module__].append((chip_name, entry))

    # Generate documentation for each module
    for module_name, chips_in_module in modules.items():

        # Load the module to access its docstring
        try:
            module = importlib.import_module(module_name)
            module_doc = module.__doc__.strip() if module.__doc__ else "No module documentation available."
        except Exception as e:
            module_doc = f"Failed to load module docstring: {e}"

        mod_name = module_name.replace("reasonchip.chipsets.","")

        url_path = mod_name.replace(".", "/")

        ctx = {
            "mod_name": mod_name,
            "url_path": url_path,
            "module_doc": module_doc,
            "chips_in_module": chips_in_module,
            "today": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
        }

        # Chip template is a Jinja2 template
        html = tmpl.render(ctx)


        # Write to file
        module_filename = os.path.join(output_dir, f"{mod_name.replace('.', '_')}.html")
        with open(module_filename, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Generated {module_filename}")


def generate_menu(menu_file: str, output_dir: str):
    """ Generate a Hugo menu file listing all modules. """
    module_files = sorted(f for f in os.listdir(output_dir) if f.endswith(".html"))

    menu_content = "<!-- Auto-generated menu -->\n"
    menu_content += "<ul>\n"
    for module_file in module_files:
        module_name = module_file.replace(".html", "").replace("_", ".")
        menu_content += f'  <li><a href="/chipsets/{module_file.replace(".html", "")}/">{module_name}</a></li>\n'
    menu_content += "</ul>\n"

    with open(menu_file, "w", encoding="utf-8") as f:
        f.write(menu_content)

    print(f"Generated menu at {menu_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate documentation for chips.")
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Output directory for documentation pages",
    )
    parser.add_argument(
        "--out-menu",
        required=True,
        help="Output path for chip menu",
    )
    parser.add_argument(
        "--chipset-template",
        required=True,
        help="Template file to use for chipsets",
    )
    args = parser.parse_args()

    with open(args.chipset_template, "r", encoding="utf-8") as f:
        chip_template = f.read()

    generate_module_docs(args.out_dir, chip_template)
    generate_menu(args.out_menu, args.out_dir)


if __name__ == "__main__":
    main()
