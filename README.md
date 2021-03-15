<div align="center" markdown>
<img src="https://i.imgur.com/pCcPRZn.png"/>

# Flying Objects

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Use">How To Use</a>
</p>


[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/flying-objects)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/flying-objects)
[![views](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/flying-objects&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/flying-objects&counter=downloads&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/flying-objects&counter=runs&label=runs)](https://supervise.ly)

</div>

# Overview

App generates synthetic data for detection / segmentation / instance segmentation tasks. It copies labeled objects (foregrounds), applies augmentations and pastes them to background images.

# How To Use


1. Label several objects as foregrounds, you can use `Seeds` project from ecosystem.


1. Add app from ecosystem to your team

<img  data-key="sly-module-link" data-module-slug="supervisely-ecosystem/flying-objects" src="https://i.imgur.com/wxe0fR7.png" width="300"/>   

2. Label foregrounds with polygons or masks. You can use demo images from project [`Seeds`](https://ecosystem.supervise.ly/projects/seeds) from Ecosystem

<img  data-key="sly-module-link" data-module-slug="supervisely-ecosystem/seeds" src="https://i.imgur.com/E5xmBRH.png" width="300"/>   

3. Prepare backgrounds - it is a project or dataset with background images. You can use dataset `01_backgrounds` from project `Seeds` as example

4. Run app from the context menu of project with labeled foregrounds:

<img src="https://i.imgur.com/6i0Z8Nm.png"/>

5. Generate synthetic data with different settings and save experiments results to different projects / datasets.

6. Close app manually


# Screenshots