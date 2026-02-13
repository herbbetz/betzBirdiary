# make_labels_common_en.py

LATIN_INPUT = "birdlabels-lat.txt"
OUTPUT = "bird_labels_en_latin.txt"

# English names for common German / European birds
COMMON_ENGLISH = {
    "Passer domesticus": "House Sparrow",
    "Passer montanus": "Eurasian Tree Sparrow",
    "Turdus merula": "Eurasian Blackbird",
    "Turdus pilaris": "Fieldfare",
    "Parus major": "Great Tit",
    "Cyanistes caeruleus": "Blue Tit",
    "Erithacus rubecula": "European Robin",
    "Pica pica": "Eurasian Magpie",
    "Garrulus glandarius": "Eurasian Jay",
    "Corvus corone": "Carrion Crow",
    "Corvus cornix": "Hooded Crow",
    "Corvus corax": "Common Raven",
    "Sturnus vulgaris": "European Starling",
    "Fringilla coelebs": "Common Chaffinch",
    "Chloris chloris": "European Greenfinch",
    "Spinus spinus": "Eurasian Siskin",
    "Pyrrhula pyrrhula": "Eurasian Bullfinch",
    "Carduelis carduelis": "European Goldfinch",
    "Columba palumbus": "Common Wood Pigeon",
    "Columba livia": "Rock Dove",
    "Motacilla alba": "White Wagtail",
    "Motacilla cinerea": "Grey Wagtail",
    "Motacilla flava": "Yellow Wagtail",
    "Troglodytes troglodytes": "Eurasian Wren",
    "Prunella modularis": "Dunnock",
    "Sylvia atricapilla": "Eurasian Blackcap",
    "Phylloscopus collybita": "Common Chiffchaff",
    "Phoenicurus phoenicurus": "Common Redstart",
    "Phoenicurus ochruros": "Black Redstart",
    "Saxicola rubicola": "European Stonechat",
    "Saxicola rubetra": "Whinchat",
    "Alauda arvensis": "Eurasian Skylark",
    "Picus viridis": "European Green Woodpecker",
    "Dendrocopos major": "Great Spotted Woodpecker",
    "Falco tinnunculus": "Common Kestrel",
    "Buteo buteo": "Common Buzzard",
    "Accipiter nisus": "Eurasian Sparrowhawk",
    "Ciconia ciconia": "White Stork",
    "Ardea cinerea": "Grey Heron",
    "Fulica atra": "Common Coot",
    "Cygnus olor": "Mute Swan",
    "Anser anser": "Greylag Goose",
    "Anas platyrhynchos": "Mallard",
    "Anas crecca": "Eurasian Teal",
    "Aythya fuligula": "Tufted Duck",
    "Podiceps cristatus": "Great Crested Grebe",
    "Tachybaptus ruficollis": "Little Grebe",
    "Vanellus vanellus": "Northern Lapwing",
    "Haematopus ostralegus": "Eurasian Oystercatcher",
    "Numenius arquata": "Eurasian Curlew",
    "Tringa totanus": "Common Redshank",
    "Actitis hypoleucos": "Common Sandpiper",
    "Calidris alpina": "Dunlin",
    "Chroicocephalus ridibundus": "Black-headed Gull",
    "Larus canus": "Common Gull",
    "Larus argentatus": "Herring Gull",
    "Larus fuscus": "Lesser Black-backed Gull",
    "Larus marinus": "Great Black-backed Gull",
    "Upupa epops": "Eurasian Hoopoe",
    "Merops apiaster": "European Bee-eater",
    "Cuculus canorus": "Common Cuckoo",
    "Emberiza citrinella": "Yellowhammer",
    "Emberiza schoeniclus": "Reed Bunting",
    "Emberiza calandra": "Corn Bunting",
    "Sitta europaea": "Eurasian Nuthatch",
    "Lanius collurio": "Red-backed Shrike",
    "Hirundo rustica": "Barn Swallow",
    "Delichon urbicum": "Common House Martin",
    "Riparia riparia": "Sand Martin",
    "Apus apus": "Common Swift",
}

with open(LATIN_INPUT, encoding="utf-8") as f:
    latin_names = [line.strip() for line in f if line.strip()]

output_lines = []

for latin in latin_names:
    english = COMMON_ENGLISH.get(latin, latin)
    output_lines.append(f"{english} / {latin}")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"Written {len(output_lines)} labels to {OUTPUT}")
