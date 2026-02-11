# make_labels_common_de.py

LATIN_INPUT = "birdlabels-lat.txt"
OUTPUT = "bird_labels_de_latin.txt"

# German names for common German / European birds
COMMON_GERMAN = {
    "Passer domesticus": "Haussperling",
    "Passer montanus": "Feldsperling",
    "Turdus merula": "Amsel",
    "Turdus pilaris": "Wacholderdrossel",
    "Parus major": "Kohlmeise",
    "Cyanistes caeruleus": "Blaumeise",
    "Erithacus rubecula": "Rotkehlchen",
    "Pica pica": "Elster",
    "Garrulus glandarius": "Eichelhäher",
    "Corvus corone": "Rabenkrähe",
    "Corvus cornix": "Nebelkrähe",
    "Corvus corax": "Kolkrabe",
    "Sturnus vulgaris": "Star",
    "Fringilla coelebs": "Buchfink",
    "Chloris chloris": "Grünfink",
    "Spinus spinus": "Zeisig",
    "Pyrrhula pyrrhula": "Gimpel",
    "Carduelis carduelis": "Stieglitz",
    "Columba palumbus": "Ringeltaube",
    "Columba livia": "Felsentaube",
    "Motacilla alba": "Bachstelze",
    "Motacilla cinerea": "Gebirgsstelze",
    "Motacilla flava": "Schafstelze",
    "Troglodytes troglodytes": "Zaunkönig",
    "Prunella modularis": "Heckenbraunelle",
    "Sylvia atricapilla": "Mönchsgrasmücke",
    "Phylloscopus collybita": "Zilpzalp",
    "Phoenicurus phoenicurus": "Gartenrotschwanz",
    "Phoenicurus ochruros": "Hausrotschwanz",
    "Saxicola rubicola": "Schwarzkehlchen",
    "Saxicola rubetra": "Wiesenpieper",
    "Alauda arvensis": "Feldlerche",
    "Picus viridis": "Grünspecht",
    "Dendrocopos major": "Buntspecht",
    "Falco tinnunculus": "Turmfalke",
    "Buteo buteo": "Mäusebussard",
    "Accipiter nisus": "Sperber",
    "Ciconia ciconia": "Weißstorch",
    "Ardea cinerea": "Graureiher",
    "Fulica atra": "Blässhuhn",
    "Cygnus olor": "Höckerschwan",
    "Anser anser": "Graugans",
    "Anas platyrhynchos": "Stockente",
    "Anas crecca": "Krickente",
    "Aythya fuligula": "Reiherente",
    "Podiceps cristatus": "Haubentaucher",
    "Tachybaptus ruficollis": "Zwergtaucher",
    "Vanellus vanellus": "Kiebitz",
    "Haematopus ostralegus": "Austernfischer",
    "Numenius arquata": "Großer Brachvogel",
    "Tringa totanus": "Rotschenkel",
    "Actitis hypoleucos": "Flussuferläufer",
    "Calidris alpina": "Sanderling",
    "Chroicocephalus ridibundus": "Lachmöwe",
    "Larus canus": "Kleine Möwe",
    "Larus argentatus": "Silbermöwe",
    "Larus fuscus": "Heringsmöwe",
    "Larus marinus": "Mantelmöwe",
    "Upupa epops": "Wiedehopf",
    "Merops apiaster": "Bienenfresser",
    "Cuculus canorus": "Kuckuck",
    "Emberiza citrinella": "Goldammer",
    "Emberiza schoeniclus": "Rohrammer",
    "Emberiza calandra": "Ackerammer",
    "Sitta europaea": "Kleiber",
    "Lanius collurio": "Neuntöter",
    "Hirundo rustica": "Rauchschwalbe",
    "Delichon urbicum": "Mehlschwalbe",
    "Riparia riparia": "Uferschwalbe",
    "Apus apus": "Mauersegler",
}

with open(LATIN_INPUT, encoding="utf-8") as f:
    latin_names = [line.strip() for line in f if line.strip()]

output_lines = []

for latin in latin_names:
    german = COMMON_GERMAN.get(latin, latin)
    output_lines.append(f"{german} / {latin}")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"Written {len(output_lines)} labels to {OUTPUT}")
