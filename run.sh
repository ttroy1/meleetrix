sudo pkill -f main.py
sudo pkill -f index.js
sudo python3 main.py --led-rows=64 --led-cols=64 --led-gpio-mapping='adafruit-hat' --led-slowdown-gpio=3 &
sleep 2
sudo nohup node index.js &
