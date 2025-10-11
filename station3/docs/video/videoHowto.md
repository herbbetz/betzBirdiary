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

- Bridge Clip between 2 Videos:
  Use MS Clipchamp or better:
  
  1. Turn still image into 2-second video:
  
  ​            without image:
  ​        ffmpeg -f lavfi -i color=color=white:size=1920x1080:duration=2:rate=30 white.mp4
  ​        transparent: ffmpeg -f lavfi -i color=color=black@0.0:s=1920x1080:d=2 -pix_fmt yuva444p -c:v libx264 -t 2 transparent.mp4
  
  ​            with image 'bridge.jpg':
  ​        ffmpeg -loop 1 -i bridge.jpg -t 2 -r 30 -vf "scale=1920:1080" -c:v libx264 -pix_fmt yuv420p bridge.mp4
  ​            -loop 1 → loops the image as a video frame source.
  ​            -t 2 → duration 2 seconds.
  ​            -r 30 → set frame rate to 30 fps (match your videos).
  ​            -vf "scale=1920:1080" → ensures the image matches the video resolution.
  ​            -pix_fmt yuv420p → ensures wide compatibility.
  
  2. Create a text file called list.txt:
     file 'video1.mp4'
     file 'bridge.mp4'
     file 'video2.mp4'
  
  3. Concatenate the clips:
     ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4
     If your videos don’t all share the same format/codec/frame rate, use re-encoding:
         ffmpeg -f concat -safe 0 -i list.txt -c:v libx264 -crf 18 -preset veryfast -c:a aac output.mp4
