// ttroy, 2023
// Melee LED Matrix Script
// Modified version of vinceau's Slippi or Dolphin mirroring example
// Reference link: 

// ----------------------------------------------------------------------------
// Import default slp-realtime libraries
const fs = require("fs");
const { tap, map, filter } = require("rxjs/operators");
const { Ports } = require('@slippi/slippi-js')
// Websocket
const WebSocket = require('ws');
// Meleetrix Configuration Settings
const settings = require('./config.json');

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { ConnectionStatus, SlpLiveStream, SlpRealTime, getStageInfo, getCharacterInfo, getCharacterColorName} = require("@vinceau/slp-realtime");

// ----------------------------------------------------------------------------
// Set the address values for connecting to Dolphin/Wii
// First, check if the active connection is console or Dolphin based
if (settings.active_conn_type == "console") {
	var ADDRESS = settings.console_address; 
	var connectionType = "console";
}
else {
	var ADDRESS = settings.slippi_dolphin_address
	var connectionType = "dolphin";
}

const PORT = Ports.DEFAULT;  

// Connect to Dolphin or the relay
const livestream = new SlpLiveStream(connectionType, {
  outputFiles: false,
});

// Connect to the livestream
livestream.start(ADDRESS, PORT)
  .then(() => {
    console.log("Connected to Slippi");
  })
  .catch(console.error);

// Write out the files when we've been disconnected
livestream.connection.on("statusChange", (status) => {
  if (status === ConnectionStatus.DISCONNECTED) {
    console.log("Disconnected from the relay.");
  }
});

// Connecting to the relay with the connection parameters
const realtime = new SlpRealTime();
// Reading from the SlpLiveStream object
realtime.setStream(livestream);

// ----------------------------------------------------------------------------
// Socket Data

// Create Websocket
const ws = new WebSocket('ws://localhost:8081');

ws.on('open', function() {
	// Connection is established, ready to send data
	console.log("Socket connection established")
});

// Data Function
function sendData(dataStr) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(dataStr);
    } else {
        setTimeout(sendData, 100); // Retry in 100ms
    }
}

// ----------------------------------------------------------------------------
// We can choose exactly which events we want to subscribe for
// by using the pipe command. Learn more by reading the RxJS docs.
realtime.game.start$.subscribe(payload => {
	// Game Start Payload - Write to file
	// GameStartType
		// slpVersion: string | null
		// isTeams: boolean | null
		// isPAL: boolean | null
		// stageId: number | null
		// players: PlayerType[]
	
	// Extract data from payload using built in functions
	payload.stageInfo = getStageInfo(payload.stageId);
	// Iterate over each character in players, adding character info
	for (let player of payload.players) {
		player.characterInfo = getCharacterInfo(player.characterId)
		player.CharacterColorName = getCharacterColorName(player.characterId, player.characterColor)
	}

	payload.messageType = 'gameStart'
	dataString = JSON.stringify(payload);
	sendData(dataString);
});

// Game End
realtime.game.end$.subscribe(payload => {
	payload.messageType = 'gameEnd'
	dataString = JSON.stringify(payload);
	sendData(dataString);
})
	  
// Stock Percentage Tracker
realtime.stock.percentChange$.subscribe((payload) => {
	// Integer; player indexes of 1-4
	const player = payload.playerIndex + 1;
	payload.messageType = 'playerPercent'
	// Write to folder with player percentages
	dataString = JSON.stringify(payload);
	sendData(dataString);
});

// Stock Count Change
realtime.stock.countChange$.subscribe((payload) => {
	// Integer; player indexes of 1-4
	const player = payload.playerIndex + 1;
	payload.messageType = 'countChange'
	// Write to folder with player percentages
	dataString = JSON.stringify(payload);
	sendData(dataString);
});



