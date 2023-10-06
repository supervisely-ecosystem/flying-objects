<div align="center" markdown>
<img src="https://user-images.githubusercontent.com/106374579/182824459-291c34dc-0a5a-4c97-a297-d1ed4143c58d.png"/>

# Flying Objects

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Use">How To Use</a> •
    <a href="#Screenshots">Screenshots</a>
</p>


[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/flying-objects)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/flying-objects)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/flying-objects.png)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/flying-objects.png)](https://supervise.ly)

</div>

# Overview

App generates synthetic data for detection / segmentation / instance segmentation tasks.
It copies labeled objects (foregrounds), applies augmentations and pastes them to background images. It is highly recommended for foreground objects to be of shapes polygon or mask. Only these shapes allows to validate the quality and correctness of synthetic labels - objects overlapping and visibility thresholds. 

App also has an option to copy objects from the selected background project as a foreground objects, 
copying applies only for selected classes that are present in both foreground and background projects and have similar shapes (polygon or mask), 
e.g: foreground class: lemon (polygon or mask), and background class: lemon (polygon or mask). Labels on background images of other shapes will be ignored because they are not guarantee the correctness of synthetic results. 

For example, if object on background image is labeled with bounding box and we copy-paste random foreground object on top of it then it will be impossible to validate background object visibility. If background object became invisible, its label have to be removed from results to make sure that resulting training data is 100% accurate. But for shapes like bounding box it is impossible to do. That is the reason why original labels on both foregrounds and backgrounds have to be polygons or masks.

**Updates:**
- 2023/10/06, v1.2.6 - Objects can be generated with Edge Smoothing and Opacity.



# How To Use


1. Label several objects as foregrounds, you can use `Seeds` project from ecosystem.


2. Add app from ecosystem to your team

<img  data-key="sly-module-link" data-module-slug="supervisely-ecosystem/flying-objects" src="https://i.imgur.com/wxe0fR7.png" width="300"/>   

3. Label foregrounds with polygons or masks. You can use demo images from project [`Seeds`](https://ecosystem.supervise.ly/projects/seeds) from Ecosystem

<img  data-key="sly-module-link" data-module-slug="supervisely-ecosystem/seeds" src="https://i.imgur.com/E5xmBRH.png" width="300"/>   

4. Prepare backgrounds - it is a project or dataset with background images. You can use dataset `01_backgrounds` from project `Seeds` as example

5. Run app from the context menu of project with labeled foregrounds:

<img src="https://i.imgur.com/6i0Z8Nm.png"/>

6. Generate synthetic data with different settings and save experiments results to different projects / datasets.

7. Close app manually


**Watch demo video**:


<a data-key="sly-embeded-video-link" href="https://youtu.be/DazA1SSQOK8" data-video-code="DazA1SSQOK8">
    <img src="https://i.imgur.com/TDGyy1E.png" alt="SLY_EMBEDED_VIDEO_LINK"  style="max-width:100%;">
</a>

# Screenshots

<img src="https://i.imgur.com/izY9tR7.png"/>

