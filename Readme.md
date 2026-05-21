# Why the fork and credits
Plex has a strange behaviour that it does not allow series recording of episodes without episode numbers. I record the SRF1 Tagesschau and 10 vor 10 every day with Plex in order to watch it whenever I want and even start watching it while the episode is running. Unfortunately there is only a season number for Tagesschau and 10 vor 10 (S2026) and no episode number (S2026E365). My fork adresses this problem by adding random incremental episode numbers.

All credits go to [mathewmeconry](https://github.com/mathewmeconry) who made this parser.

# TV7_EPG_Parser
Parses teleboy.ch and init7's API for the EPG-Information and prepares them for TV7 (Init7) in XMLTV format.

# Ready XMLTV Files
https://github.com/mathewmeconry/TV7_EPG_Data

# Matching rate
~143 channels

# Requirements
- python3 >=3.7.3
- modules listed in [requirements.txt](https://github.com/mathewmeconry/TV7_EPG_Parser/blob/master/requirements.txt). (can be installed with `python3 -m pip install -r requirements.txt`)

# Discord Server
This server is used for idea discussions and some small out of topic stuff.  
Please report issues or complete feature requests with the github [issues](https://github.com/mathewmeconry/TV7_EPG_Parser/issues) feature.  
https://discord.gg/4FMXY3c

## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D


## License
MIT
