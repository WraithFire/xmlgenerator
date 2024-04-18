# Pokemon XML Generator

Generates XML files for all Pokémon, whether new or old, in a format importable by Skytemple.

## Data Generated

1. Pokémon Data
2. Moves Data
3. Abilities
4. Evolution Data
5. Mystery Dungeon Meta Data
6. Base Stats
7. Stat Growth (planned not implemented yet)
8. Exp Curve (planned not implemented yet)

## Usage

### Windows

**Executable**:

-   Download the executable file from the [Releases](https://github.com/WraithFire/xmlgenerator/releases) tab.
-   Place the executable in a separate folder.
-   Run the executable. The initial run will generate `pokemon_data.py` and a `pokemon_xml` folder.

**Run from Source**:

-   Follow the instructions for Mac/Linux.

### Mac/Linux

**Run from Source**:

-   Clone the repository using `git clone https://github.com/WraithFire/xmlgenerator.git`.
-   Navigate to the cloned directory.
-   Make sure you have Python installed on your system.
-   Run the script with `python pokemon.py`.
-   The initial run will generate a `pokemon_xml` folder.

### Tool Usage

![XML Generator](references/screenshot.png)

-   Select the Pokémon you want to generate XML for.
-   Add the selected Pokémon to the generation queue by clicking "Add Query". You can add multiple queries.
-   Click on "Generate XML" to create the XML files.
-   The generated XML will be located in the `pokemon_xml` folder.
