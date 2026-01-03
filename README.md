# BallsDex Broadcast Pack
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/rayhsueh)
> [!NOTE]
> Licensed under Apache 2.0

A standardized BallsDex 3.0 package that allows administrators to broadcast messages and images to all configured spawn channels or specific users via DMs.

## Features

*   **Global Broadcast**: Send messages and images to all configured spawn channels
*   **Direct Message Broadcast**: Send messages to specific users via DM
*   **Channel Monitoring**: List and monitor broadcast channels with statistics
*   **Farm Control**: Detect potential farming behavior in channels
*   **Attachment Support**: Support for image broadcasts
*   **Admin Controls**: Restricted to bot administrators

## Installation

1. **Configure `extra.toml`**  
   
   **If the file doesn't exist:** Create a new file `extra.toml` in your `config` folder under the BallsDex directory.
   
   **If you already have other packages installed:** Simply add the following configuration to your existing `extra.toml` file. Each package is defined by a `[[ballsdex.packages]]` section, so you can have multiple packages installed.
   
   Add the following configuration:

   ```toml
   [[ballsdex.packages]]
   location = "git+https://github.com/Ray-Hsueh/BallsDex-Broadcast-Pack.git"
   path = "broadcast"
   enabled = true
   editable = false
   ```
   
   **Example of multiple packages:**
   ```toml
   # First package
   [[ballsdex.packages]]
   location = "git+https://github.com/example/package1.git"
   path = "package1"
   enabled = true
   editable = false
   
   # Second package (Broadcast Pack)
   [[ballsdex.packages]]
   location = "git+https://github.com/Ray-Hsueh/BallsDex-Broadcast-Pack.git"
   path = "broadcast"
   enabled = true
   editable = false
   ```

2. **Build and Launch**
   ```bash
   docker compose build
   docker compose up -d
   ```

## Configuration

The broadcast system uses the standard BallsDex spawn channel configuration.
Ensure that servers have configured their spawn channel using the base BallsDex commands (e.g., `/config channel`).

## Usage

### Broadcast Commands
*   `/broadcast server [mode] [message] [attachment] [anonymous]`
    *   `mode`: Text and Image, Text Only, Image Only
    *   `message`: The content to broadcast
    *   `attachment`: Optional image file
    *   `anonymous`: Hide the sender's name

*   `/broadcast dm [message] [user_ids] [anonymous]`
    *   `message`: The content to send
    *   `user_ids`: Comma-separated list of user IDs
    *   `anonymous`: Hide the sender's name

### Management Commands
*   `/broadcast channels`
    *   Lists all configured channels with member counts and recent catch stats.

## Updating

To update the package to the latest version, run the following command to rebuild the container without using the cache:

```bash
docker compose build --no-cache
docker compose up -d
```
