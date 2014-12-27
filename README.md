## Backlagg ##

This is a partial prototype I wrote as a tool to help me generate an outline of what games I may want to play next in my steam backlog and games I should
consider revisiting. Currently scrapes times from howlongtobeat.com, which I feel terrible about but don't really have any other choice at the moment.
Will probably reimplement when time permits as something more formal. Does the job for now though and might for someone else too.

## Interpreting the output ##

Though the column layout is subject to change, the output format for suggested games to play and revisit are simple tab-separated values. The following is a
sample of the output from the main backlog summary. From left to right, the columns are as follows: Steam app ID, game name as it appears on Steam and the projected
time to complete the game. In the revisitation output there will be a column preceding the projected times. These are your own times as given by Steam.

Additionally, if a game's name had to be modified in order to get results from the search there will be a "(?)" appended to the name in the output. The final name used and the results
from it are written to the log file as well as games that times couldn't be found for.

    246680	Secrets of Rætikon                                   	3.00
    225080	Brothers - A Tale of Two Sons (?)                    	3.00
    252670	Nihilumbra                                           	3.00
    55110 	Red Faction: Armageddon                              	10.00
    204360	Castle Crashers                                      	10.00
    238460	BattleBlock Theater                                  	10.00
    245280	ENSLAVED™: Odyssey to the West™ Premium Edition (?)  	10.50
    233130	Shadow Warrior                                       	12.00
    225260	Brütal Legend                                        	12.50
    113020	Monaco                                               	14.00
    237930	Transistor                                           	14.00
    41070 	Serious Sam 3: BFE                                   	14.50
    227780	Serious Sam Classics: Revolution                     	15.00
    91700 	E.Y.E: Divine Cybermancy                             	16.00
    215530	The Incredible Adventures of Van Helsing             	16.50
    213670	South Park™: The Stick of Truth™                     	17.00
    214560	Mark of the Ninja                                    	18.50
    107100	Bastion                                              	19.50
    241540	State of Decay                                       	20.00
    20500 	Red Faction: Guerrilla Steam Edition (?)             	20.50
    250900	The Binding of Isaac: Rebirth                        	21.00
    247660	Deadly Premonition: The Director's Cut (?)           	21.00
    209080	Guns of Icarus Online                                	21.50
    212680	FTL: Faster Than Light                               	22.50
    233450	Prison Architect                                     	23.00
    200260	Batman: Arkham City GOTY                             	23.50
    200710	Torchlight II                                        	25.00
    8870  	BioShock Infinite                                    	25.50
    50620 	Darksiders                                           	26.50
    50650 	Darksiders II                                        	27.50
    23490 	Tropico 3 - Steam Special Edition (?)                	30.50
    202200	Galactic Civilizations® II: Ultimate Edition         	31.00
    233700	Sword of the Stars: The Pit                          	31.50
    206420	Saints Row IV                                        	32.50
    315260	Space Hack                                           	40.00
    239350	Spelunky                                             	44.00
    91310 	Dead Island                                          	49.00
    3170  	King's Bounty: Armored Princess                      	51.50
    25900 	King's Bounty: The Legend                            	64.00
    22330 	The Elder Scrolls IV: Oblivion                       	190.00
    222900	Dead Island: Epidemic                                	330.00

## License ##

Copyright (c) 2014+, Anthony Garcia <anthony@lagg.me>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
