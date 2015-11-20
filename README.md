[![Code Climate](https://codeclimate.com/github/d3ming/tagcompare/badges/gpa.svg)](https://codeclimate.com/github/d3ming/tagcompare)
[![Test Coverage](https://codeclimate.com/github/d3ming/tagcompare/badges/coverage.svg)](https://codeclimate.com/github/d3ming/tagcompare/coverage)
[![Issue Count](https://codeclimate.com/github/d3ming/tagcompare/badges/issue_count.svg)](https://codeclimate.com/github/d3ming/tagcompare)

╔╦╗╔═╗╔═╗  ╔═╗╔═╗╔╦╗╔═╗╔═╗╦═╗╔═╗
 ║ ╠═╣║ ╦  ║  ║ ║║║║╠═╝╠═╣╠╦╝║╣ 
 ╩ ╩ ╩╚═╝  ╚═╝╚═╝╩ ╩╩  ╩ ╩╩╚═╚═╝
 
*Scenario*: For a given creative tag, we want to make sure it looks good in all kinds of browser configs.

There are many differences and issues when trying to render an HTML5 creative under different platform/browsers.
  1. Fonts might look or **be** different
  2. CSS / layout differences
  3. Animation / timing differences

This tool tries to address the first 2 points above by doing image comparison of an HTML5 creative tag under different 
platform/browser configurations

## Setup
`make install` to install dependencies

### settings.json
Make a local copy of [`settings.json`](tagcompare/settings.json) called `settings.local.json`
Update the values for webdriver user/key and placelocal secret:
```json
  ...
  "webdriver": {
    "user": "USER",
    "key": "KEY",
    "url": "REMOTE_WEBDRIVER_URL"
    ...
  },
  "placelocal": {
    "domain": "www.placelocaldemo.com",
    "secret": {
      "pl-secret": "SECRET",
      "pl-service-identifier": "SERVICEID"
    }
  }
  ...
```

## Running the tool
`make run` will run the tool to capture screenshots and compare them

## Running tests
`make test` will run unit tests
