<!--keywords[Codedoc,selectboxes]-->

**Selectboxes**

Verzeichnisse in station3/: stations, validate, select

1. *button*: config3.html, daywatch-video.html
2. *source*: stations.js, birdlabels.js -> js object `selectData ={key1:val1,...}`
3. *select helper*: genselect.js, select.css
4. *X-selector*: selectstations.html, validate.html -> query params `selectkey=keyX&selectvalue=valX`, Backlink zu 1.
5. *layouter*: rb-reports.html, validate-confirm.html -> query params
6. *flask endpoint*: /api/report-data, /api/validation-data
7. *api agent from flask*: rarebrds4srvpag.py, validation4srv.py
