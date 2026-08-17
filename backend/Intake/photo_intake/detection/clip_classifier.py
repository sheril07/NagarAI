import open_clip
import torch
from PIL import Image


# ==========================================
# LOAD CLIP MODEL
# ==========================================

model, _, preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32",
    pretrained="openai"
)

tokenizer = open_clip.get_tokenizer("ViT-B-32")


# ==========================================
# LEVEL 1: COMPLAINT CATEGORIES
# ==========================================

# ==========================================
# CATEGORY NAMES
# ==========================================

CATEGORY_NAMES = [
    "road and transportation issue",
    "waste management issue",
    "water and drainage issue",
    "electricity and lighting issue",
    "public infrastructure issue",
    "traffic and signal issue",
    "environmental issue",
    "public safety issue",
    "animal related issue",
    "other civic issue"
]


# ==========================================
# CATEGORY PROMPTS FOR CLIP
# ==========================================

CATEGORY_PROMPTS = [
    "a photograph showing a damaged road, pothole, road crack, or roadway problem",

    "a photograph showing garbage, trash, litter, or waste in a public area",

    "a photograph showing flooding, standing water, water leakage, or a drainage problem",

    "a photograph showing a broken streetlight, electrical pole, or exposed electrical wire",

    "a photograph showing a damaged building, sidewalk, footpath, or public facility",

    "a photograph showing a broken traffic signal, traffic light, or road sign",

    "a photograph showing a fallen tree, pollution, or environmental damage",

    "a photograph showing a dangerous hazard or unsafe condition in a public area",

    "a photograph showing a stray, injured, or dead animal in a public area",

    "a photograph showing another type of civic problem"
]

# ==========================================
# LEVEL 2: SPECIFIC ISSUES
# ==========================================

ISSUES = {

    "road and transportation issue": {

        "pothole": [
            "a photograph of a pothole in a road",
            "a deep hole or depression in the road surface",
            "a large hole in asphalt caused by damaged road surface",
            "a damaged road with a visible pothole",
            "a circular or irregular hole in the pavement"
        ],

        "road crack": [
            "a photograph of cracks in a road",
            "thin cracks or long fractures across asphalt",
            "linear cracks on the surface of a paved road",
            "a road surface with visible cracks but no large holes",
            "fractures running through the asphalt surface"
        ],

        "damaged road": [
            "a severely damaged roadway",
            "a deteriorated road surface",
            "broken and uneven asphalt across a roadway",
            "a road with extensive surface damage",
            "a badly damaged paved road"
        ],

        "broken footpath": [
            "a broken pedestrian footpath",
            "a damaged sidewalk",
            "a cracked and uneven pavement for pedestrians",
            "broken pavement beside a road",
            "a damaged pedestrian walkway"
        ],

        "road obstruction": [
            "an object blocking a roadway",
            "an obstruction on a road",
            "something blocking traffic on a street",
            "a road blocked by an object",
            "an obstacle occupying part of a roadway"
        ],

        "damaged road sign": [
            "a damaged road sign",
            "a broken traffic or road sign",
            "a fallen road sign",
            "a bent or damaged sign beside a road",
            "damaged roadside signage"
        ]
    },


    "waste management issue": {

        "garbage pile": [
            "a large pile of garbage",
            "a pile of waste dumped in a public area",
            "accumulated garbage on the roadside",
            "a large collection of trash on the ground",
            "garbage accumulated in an open area"
        ],

        "overflowing garbage bin": [
            "an overflowing garbage bin",
            "a trash bin filled beyond capacity",
            "garbage spilling out of a public waste bin",
            "a completely full garbage container",
            "waste overflowing from a trash bin"
        ],

        "illegal dumping": [
            "garbage illegally dumped in a public area",
            "waste dumped on the roadside",
            "an unauthorized waste dumping area",
            "trash dumped in an inappropriate location",
            "a public area being used for illegal waste dumping"
        ],

        "scattered waste": [
            "garbage scattered across the ground",
            "scattered trash in a public area",
            "waste spread across a street",
            "litter scattered around a public space",
            "garbage spread over the ground"
        ]
    },


    "water and drainage issue": {

        "water leakage": [
            "water leaking from infrastructure",
            "visible water leakage from a pipe",
            "water leaking onto a public area",
            "a broken pipe causing water leakage",
            "water escaping from damaged infrastructure"
        ],

        "flooded road": [
            "a road covered with flood water",
            "a flooded street",
            "standing water covering a roadway",
            "significant water accumulation on a road",
            "a roadway flooded with water"
        ],

        "blocked drain": [
            "a blocked roadside drain",
            "a drainage channel blocked by debris",
            "a clogged public drainage system",
            "a drain blocked with garbage",
            "a blocked stormwater drain"
        ],

        "overflowing drain": [
            "an overflowing roadside drain",
            "wastewater overflowing from a drain",
            "a public drain overflowing onto the street",
            "a drainage system overflowing with water",
            "an overflowing sewage or stormwater drain"
        ]
    },


    "electricity and lighting issue": {

        "broken streetlight": [
            "a broken streetlight",
            "a damaged street lighting pole",
            "a non-functional streetlight",
            "a damaged public lighting fixture",
            "a streetlight that is broken or fallen"
        ],

        "damaged electrical pole": [
            "a damaged electrical pole",
            "a broken electricity pole",
            "a leaning electrical pole",
            "damaged electrical infrastructure",
            "a fallen or damaged power pole"
        ],

        "exposed electrical wire": [
            "exposed electrical wires",
            "loose electrical wires in a public area",
            "dangerously exposed power cables",
            "electrical wires hanging outside infrastructure",
            "exposed wiring creating a public hazard"
        ]
    },


    "public infrastructure issue": {

        "damaged building": [
            "a damaged public building",
            "a damaged building structure",
            "visible structural damage to a building",
            "a deteriorating public building",
            "a damaged civic building"
        ],

        "damaged footpath": [
            "a damaged public footpath",
            "a broken sidewalk",
            "an uneven pedestrian walkway",
            "damaged pavement for pedestrians",
            "a badly damaged sidewalk"
        ],

        "damaged public infrastructure": [
            "damaged public infrastructure",
            "a damaged civic facility",
            "broken public infrastructure",
            "deteriorating public facilities",
            "damage to a public facility"
        ]
    },


    "traffic and signal issue": {

        "broken traffic signal": [
            "a broken traffic signal",
            "a damaged traffic light",
            "a non-functional traffic signal",
            "a damaged signal at an intersection",
            "a broken traffic light"
        ],

        "damaged traffic sign": [
            "a damaged traffic sign",
            "a broken traffic sign",
            "a fallen traffic sign",
            "a bent traffic sign",
            "damaged signage at a road"
        ],

        "traffic obstruction": [
            "an obstruction causing a traffic problem",
            "something blocking traffic",
            "a road obstruction causing traffic",
            "an object blocking vehicles",
            "a blocked roadway"
        ]
    },


    "environmental issue": {

        "fallen tree": [
            "a fallen tree on a road",
            "a tree that has fallen across a public area",
            "a fallen tree blocking a street",
            "a large fallen tree",
            "a tree fallen onto a roadway"
        ],

        "air pollution": [
            "visible air pollution",
            "heavy smoke pollution in a public area",
            "a scene showing severe air pollution",
            "smoke causing environmental pollution",
            "polluted air in an urban area"
        ],

        "environmental damage": [
            "visible environmental damage",
            "damage to a natural public area",
            "environmental degradation",
            "damage to the surrounding environment",
            "a polluted or damaged natural area"
        ]
    },


    "public safety issue": {

        "dangerous structure": [
            "a dangerous damaged structure",
            "an unsafe structure in a public area",
            "a structure that appears at risk of collapsing",
            "a hazardous damaged structure",
            "an unsafe public structure"
        ],

        "unsafe road condition": [
            "an unsafe road condition",
            "a dangerous roadway",
            "a hazardous road surface",
            "a road creating a public safety hazard",
            "a dangerous condition on a road"
        ],

        "public hazard": [
            "a dangerous public hazard",
            "a visible hazard in a public area",
            "an object creating a public safety risk",
            "a dangerous situation in a public space",
            "a hazard affecting pedestrians or vehicles"
        ]
    },


    "animal related issue": {

        "stray animal": [
            "a stray animal in a public area",
            "an animal wandering on a road",
            "a stray animal on a street",
            "an unattended animal in a public space",
            "an animal causing a road safety concern"
        ],

        "injured animal": [
            "an injured animal in a public area",
            "an animal that appears injured",
            "an injured animal on a road",
            "a visibly hurt animal",
            "an animal requiring assistance"
        ],

        "dead animal on road": [
            "a dead animal lying on a road",
            "an animal carcass on a roadway",
            "a deceased animal blocking a road",
            "a dead animal in a public area",
            "an animal that appears to be dead on a street"
        ]
    },


    "other civic issue": {

        "other civic problem": [
            "a public civic problem",
            "an issue affecting public infrastructure",
            "a problem in a public area",
            "a civic issue requiring attention",
            "an urban public problem"
        ]
    }
}


# ==========================================
# CLASSIFICATION FUNCTION
# ==========================================

def classify_image(image_path):

    # --------------------------------------
    # Load image
    # --------------------------------------

    image = Image.open(image_path).convert("RGB")

    image = preprocess(image)

    image = image.unsqueeze(0)


    # --------------------------------------
    # Create image embedding
    # --------------------------------------

    with torch.no_grad():

        image_features = model.encode_image(image)

        image_features /= image_features.norm(
            dim=-1,
            keepdim=True
        )


    # ======================================
    # LEVEL 1 — CATEGORY
    # ======================================

    category_tokens = tokenizer(CATEGORY_PROMPTS)
    with torch.no_grad():
        category_features = model.encode_text(category_tokens)
        category_features /= category_features.norm(
            dim=-1,
            keepdim=True
        )
        category_scores = (image_features @ category_features.T)

        category_index = category_scores[0].argmax().item()
        category = CATEGORY_NAMES[category_index]


    # ======================================
    # LEVEL 2 — SPECIFIC ISSUE
    # ======================================

    issue_data = ISSUES[category]

    best_issue = None
    best_score = float("-inf")


    for issue_name, prompts in issue_data.items():

        issue_tokens = tokenizer(prompts)

        with torch.no_grad():

            issue_features = model.encode_text(
                issue_tokens
            )

            issue_features /= issue_features.norm(
                dim=-1,
                keepdim=True
            )

            scores = (
                image_features @ issue_features.T
            )

            # Average multiple prompts
            score = scores.mean().item()


        if score > best_score:

            best_score = score

            best_issue = issue_name


    issue = best_issue


    # ======================================
    # RETURN RESULTS
    # ======================================

    return category, issue