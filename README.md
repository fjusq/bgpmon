# BGPmon

## Description
A container to log route changes with syslog.
It uses bird to peer over BGP, and collect routes. It is basicly a route collector.
This is a tool that I mostly buildt for myself. Please note that I am not a developer, just a regular network engineer that like to string together tools that makes life easier for me. Any feedback on how to improve or implement stuff better are always appriciated :)
If you would like to know how I got in to build this project, [this blogpost](https://fjusq.wordpress.com/2025/09/01/peering-into-the-void-bgp-visibility-in-azure-and-meraki/) give some background and uses cases. You might regret tough, it is porbarbly not very interesting.

## Installation
The installation is pretty straight forward.

```
#Clone this repo
git clone https://github.com/fjusq/bgpmon.git && cd bgpmon
#Copy the example env and edit the parameters
cp env.example .env && nano .env
#Enjoy the show:
docker compose up -d
```

You can now enjoy havin logs from route changes from your BGP peers:
```
 docker compose logs -f
```
<img width="783" height="287" alt="image" src="https://github.com/user-attachments/assets/06f5d04c-962f-4bad-858d-3b96423a041c" />


## Credits
This project builds on the great work of:  
- [BIRD Internet Routing Daemon](https://bird.network.cz/)  
- [Net-SNMP](http://www.net-snmp.org/)  
- [rsyslog](https://www.rsyslog.com/)  

All credit goes to their authors and communities.  
This project simply integrates and packages them for monitoring purposes.

## Contributions
An honest thanks to ChatGPT. As a noob in both docker and coding it has been helpfull to have someone that answers even the most stupid question!

## Devstuff

Changelog (mostly for my own tracking):
```
Started over with a new code base using Alpine.
```
The syslog and SNMP output is not necessarily very usefull yet. I will look into this very soon.
I have just tested that it works and gives some output. 

Roadmap:
```
Add support for SNMP
```
