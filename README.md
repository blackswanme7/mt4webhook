# MT4 orderplacement from tradingview without keep your computer on 

This is a webserver code that will need to deploy , it will generate a link after posting that webhook in the tradingview it will place order 

### Installation 
- Install python 
- Clone this repo 
- Install the requirements 
- FIll up the credentials 

## run the app 
`gunicorn -w 4 -b 0.0.0.0:80 main:app`


## message 

buy 

`[{"symbol":"GBPUSD.HKT","lot":"1","side":"buy"}]`

sell 
`[{"symbol":"GBPUSD.HKT","lot":"1","side":"sell"}]`

exit
`[{"symbol":"GBPUSD.HKT","lot":"0","side":"buy","exit":"0"}]`


## only open one position . 