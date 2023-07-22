# Meleetrix v1.0

Display local scores of Slippi-based instances of Super Smash Brothers Melee on an LED matrix.

---------------

Meleetrix is a lightweight Python script to display information received from vinceau's [slp-realtime](https://github.com/vinceau/slp-realtime) library on a 64x64 LED Matrix. The character, color, percentage, and number of stocks are presented in a scoreboard-style layout. Games played on consoles running Slippi Nintendont or through Slippi Dolphin are supported.

Running this project requires a Raspberry Pi and a 64x64 LED display.

The hardware this project was developed and tested with is listed below. Where applicable, links to the product's page on Adafruit have been listed. As of writing (July 2023), you may have difficulty finding the Pi 3/Pi 4 available for sale outside of the secondary market.

#### Display States

##### *4P Games (Grid)*
![alt text](https://github.com/ttroy1/meleetrix/blob/main/assets/images/fourPlayerGrid.jpeg)

##### *4P Games (List)*: [Image](https://github.com/ttroy1/meleetrix/blob/main/assets/images/fourPlayerRows.jpeg)

##### *3P Games*: [Image](https://github.com/ttroy1/meleetrix/blob/main/assets/images/threePlayers.jpeg)

##### *2P Games*: [Image](https://github.com/ttroy1/meleetrix/blob/main/assets/images/twoPlayers.jpeg)

##### Winner Screen: [Image](https://github.com/ttroy1/meleetrix/blob/main/assets/images/winner.jpeg)

##### Pregame and Postgame: [Image](https://github.com/ttroy1/meleetrix/blob/main/assets/images/waiting.jpeg)

## Installation

### Hardware Assembly

For a great guide on the parts required and their assembly, see the wiki provided in the mlb-led-scoreboard library, linked [here](https://github.com/MLB-LED-Scoreboard/mlb-led-scoreboard/wiki).

Note that the guide mentions 32x32 and 64x32 displays, while this project only supports 64x64 displays. Using a 64x64 display with the Adafruit bonnet does require a small amount of soldering; specific instructions for this are available [on Adafruit](https://learn.adafruit.com/adafruit-rgb-matrix-bonnet-for-raspberry-pi/driving-matrices). Adafruit has several different versions of 64x64 displays available, each with varying space between each pixel (called 'pitch'), which changes the overall size of the display. Consider choosing a pitch based on your expected viewing distance from the display - the closer you are, the smaller your pitch should be.

* [2mm Pitch](https://www.adafruit.com/product/5362)
* [2.5mm Pitch](https://www.adafruit.com/product/3649)
* [2.5mm Pitch, Curb-Cut](https://www.adafruit.com/product/5407)
* [3mm Pitch](https://www.adafruit.com/product/4732)

#### Hardware Pictured
Outside of the linked microSD card, these are the parts used for the example photos provided:

* [Raspberry Pi 3B+](https://www.adafruit.com/product/3775)
* [64x64 LED Matrix, 2.5mm Pitch](https://www.adafruit.com/product/3649)
* [5V 10A Power Supply](https://www.adafruit.com/product/658)
* [RGB Matrix Bonnet](https://www.adafruit.com/product/3211)
* [microSD Card](https://www.adafruit.com/product/1294)

### Software Installation

#### Installing repository and required libraries

The files included in this repo are designed to run directly on your Pi. SSH into your Pi and enter the following commands into bash as needed.

If Git is not already installed on your machine, install it now:
```bash
sudo apt-get update
sudo apt-get install git python3-pip
```

Next, install this repository and its requirements:
```bash
git clone https://github.com/ttroy1/meleetrix
cd meleetrix
pip install -r requirements.txt
```

To run index.js, install slp-realtime. ```rxjs``` and ```@slippi/slippi-js``` are both peer dependencies of slp-realtime. Node will need

Javascript setup (slp-realtime)

```bash
install
```

Install git repo

#### Once repository is installed

*Dolphin*

* Find the IP address of your personal computer. If unsure on how to do this, consider using an application such as [Angry IP Scanner](https://angryip.org/) to see all of the devices on your network.

*Console*
* If using a console, see Nikki's [Slippi Console Mirroring Guide](https://docs.google.com/document/d/1ezavBjqVGbVO8aqSa5EHfq7ZflrTCvezRYjOf51MOWg/edit). Installations of Homebrew and Nintendont Slippi on your Wii are prerequisites for mirroring. Separate documents on how to set these up are linked to from the mirroring guide.

Once you've obtained the IP address of your device, add it as the *Console Address* or *Slippi Dolphin Address* in Meleetrix's config.json file, located in the repo's home directory. 

Be sure to update the *Active Connection Type* field to the appropriate value as well. For more information on config.json and customization, see the [Customization](https://github.com/ttroy1/meleenotes/edit/main/README.md#customization) section of this document.


### Usage

I recommend against starting the script while a game is in progress - while slp-realtime will generally catch up to the current game state, there can also be unexpected behavior.


### Customization

There are several elements within Meleetrix available to be customized by the user. In the project's home directory, an example config.json file has been provided that contains each of these fields. The options available for each of these elements are outlined below:

| Name                                    | Description | Path        | Type     | Example     |
| :---                                          |    :---     |     :--- | :--- | :--- |
| Backgrounds Active (General)                            | Toggles whether background colors are enabled as a whole, which includes the default character/color-specific backgrounds. | colors:backgrounds_active       | Bool | true |
| Custom Backgrounds Active                 | Toggles whether character/color specific background colors are enabled. The provided default background colors will be disabled as well. | colors:custom_backgrounds_active      | Bool | false |
| Background Colors (Character/Color Specific) | A dictionary of character/color specific background colors. The full list of character/color names can be found in the meleetrix/assets/icons folder.       | colors:custom_char_bgs       | Dict | {"falcon-green": [14, 74, 46]} |
| Custom Foregrounds Active | Toggles whether character/color specific background colors are enabled.             | colors:custom_foregrounds_active       | Bool | false |
| Foreground Colors (Character/Color Specific) | A dictionary of character/color specific foreground colors. The full list of character/color names can be found in the meleetrix/assets/icons folder.            | colors:custom_char_fgs      | Dict | {"falcon-green": [255, 255, 255]} |
| Toggle Border (General) | While in list view, toggles whether borders are displayed around each player's section.         | colors:borders_active      | List | false |
| Border Color (General)                           | If borders are active, the color provided here is what will be displayed.         | colors:borders_rgb | Array | [255, 255, 255]
| Toggle 4P Grid View                           | Toggles whether list view or grid view is used for 4P gameplay. By default, grid view is enabled. | grid_view_4p        | Bool | true |
| Active Connection Type                        | Used to determine whether you're using a console or Dolphin-based connection.        | active_conn_type     | String | "dolphin" *or* "console" |
| Console Address                      | The IP address of your console running Slippi Nintendont. | console_address      | String | "192.168.0.0" |
| Slippi Dolphin Address               | The IP address of your PC running Slippi Dolphin. | slippi_dolphin_address      | String | "192.168.0.0" |

## Acknowledgements

If you like this project, consider supporting those in the Melee community who made it possible:

[slp-realtime](https://github.com/vinceau/slp-realtime)

[project-slippi](https://github.com/project-slippi/project-slippi)
  * [Donate or subscribe to Slippi](https://slippi.gg)

## Licensing










