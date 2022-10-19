# Parsr-utils
Utils for interacting with the PDF parser Parsr

## Requirements
- Python 3.10 (haven't tested it, but will probably work with previous versions)  
- [Docker](https://www.docker.com/)
- Containers from [Parsr](https://github.com/axa-group/Parsr)
  - docker pull axarev/parsr

## Guide

The utils functions will take of managing the docker container, so docker needs to be running before you run the code.

Four differnt config files have been provided.

### Default config
The [defult config](config/default_config.json) as provided by Parsr.

### Stable config
The [stable config](config/stable_config.json) is the default, but without the ml_heading_detection and link_detection modules. With the default config these two modules are really really slow and should only be used if you have time to wait for a few days depending on the document.

### ML Heading Detection config
The [ml_heading_detection config](config/ml_heading_config.json) changes the pdf extractor from `pdfminer` (default extractor) to `pdfjs`. When using `pdfminer` my patience wore out after some of the document had been running for 8 hours. With `pdfjs` this was greatly improved. 150 documents were parsed without issue most only took a few minutes while the ones that I timed out after 8 hours now took between 2 to 4 hours which was a major improvement and in my case running this was a one time step so the time was acceptable.

This module can be quite useful as it detects the different headings in the document which makes it easier to keep the original hieracrhy of the PDF.

### Link Detection config
The [link_detection config](config/link_detection_config.json) is the stable config but withlink detection activated. I didn't need this so haven't done any testing with this module, but the config is provided as it was removed from the default.

This module is meant to detect `urls`, `goto`, and `mailto` type of links. It might be useful depending on you use case, but for me this was irrelevant.

### Constants
The [constants file](utils/constants.py) contains some default values that can be tuned to your preference.

Constant       | Default Value                           | Description
---------------|-----------------------------------------|---------------
IMAGE          | axarev/parser                           | Image name of the Parsr, this is the default name provided by Parsr
ATTEMPT_LIMIT  | 1                                       | Number of attempts per file, initial attempt included
DOCKER_TIMEOUT | 1800 (seconds)                          | Docker container will restart if there is a timeout. Default set to 30 min, big documents make take longer so feel free to increase this.
URLS           | http://localhost:3001/api/v1/{endpoint} | The endpoints relative to localhost

### Notebook for running the parser
The [parser notebook](pdf_parser.ipynb) can be used to interact with the parser.
You can of course also call the functions from [parsr_utils](utils/parsr_utils.py) directly.
