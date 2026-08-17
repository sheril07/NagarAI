# NagarAI
Categories: - 
Category                                  | Example complaints                                                                           
Roads & Traffic              | Potholes, damaged roads, fallen trees blocking roads, broken traffic signals   
Water & Drainage             | Water leakage, burst pipes, flooding, blocked drains                         
Waste Management             | Garbage piles, overflowing bins, illegal dumping                               
Street Lighting & Electricity | Broken streetlights, exposed wires, power-related hazards                             
Infrastructure Damage      | Damaged buildings, bridges, sidewalks, public facilities                        
Public Safety               | Dangerous locations, exposed electrical infrastructure, fire hazards                        
Public Health & Sanitation   | Sewage overflow, stagnant water, unhygienic public areas                          
Public Transport            | Damaged bus stops, unsafe stops, obstruction affecting transit                  
Other / General              | Complaints that don't fit elsewhere                                         


eg template
{

  "input_type": "photo",

  "category": "road_transport",

  "issue": "pothole",
 

  "description": "Large pothole detected on the roadway.",

  "latitude": 12.XXXX,

  "longitude": 80.XXXX,

  "location": "Chennai",

  "severity_features": {

    "size": "large", (only for photos) 

    people affected 

    "public_safety_risk": true

  }

}

 Geo-distance 📍

This uses the latitude and longitude of reports and calculates how physically close they are.

For example:

Report A: (12.85, 80.22)
Report B: (12.851, 80.221)

They're geographically close.

This can be calculated using something like the Haversine distance formula. You don't necessarily need a geolocation API for this.
