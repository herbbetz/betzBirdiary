<!--keywords[FFMPEG, Video_nachbearbeiten, Zeitlupe]-->

Videos können in **VLC** mit der **E-Taste** im Einzelbildmodus betrachtet werden.

Die Videobearbeitung erfolgt am besten mit **FFMPEG**:

- Zerlegung: **ffmpeg -i input.mp4 -qscale:v 2 frame%05d.jpg **
	qscale value ranges from 2-31, where 2 is best quality and 31 is worst (verzichtbar: -vf fps=30)
	
- Synthese: **ffmpeg -framerate 2 -start_number 12 -i frame%05d.jpg -c:v libx264 -r 2 -pix_fmt yuv420p output.mp4**
	-framerate 2 at the beginning sets the input frame rate, telling FFmpeg to read the input images at 2 frames per second.
	-r 2 near the end sets the output frame rate, ensuring the final video has 2 frames per second.
	In this case, both the input and output frame rates are set to 2, which means the timing of the input images will be preserved in the output video.
	If these values were different, FFmpeg would either duplicate or drop frames to match the desired output frame rate.

	Dabei muss die Startnummer angepasst werden. Werden Frames aus der Mitte gelöscht, muss die Kontinuität der Frame-Nummern wiederhergestellt werden, z.B. mit dem Utility 'framegap.py'. Sollen mehrere Videos mit gleichen Frame-Nummern vereinigt werden, hilft das 'Batch Rename(B)' von Irfanview.

