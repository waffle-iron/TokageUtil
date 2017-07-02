#!/usr/bin/env python
# -*- coding: utf-8 -*-

import http.client
import httplib2
import os, random, sys, time
from threading import Lock
from . import fileutil

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Developers Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = os.path.expanduser('~/.OAUTH/google_client_id.json')

SECRET_FILE = os.path.expanduser('~/.OAUTH/secrets.yml')
DEVELOPER_KEY = fileutil.readYamlSetting(SECRET_FILE)['DEVELOPER_KEY']

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
Y2B_SCOPE_BASE = 'https://www.googleapis.com/auth/'
YOUTUBE_SCOPES = {
                    'UPLOAD': Y2B_SCOPE_BASE + 'youtube.upload',
                    'READONLY': Y2B_SCOPE_BASE + 'youtube.readonly'
                  }
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

shrot_url = 'youtu.be/%s?a'
# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(CLIENT_SECRETS_FILE)

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")
VALID_BROADCAST_STATUSES = ("all", "active", "completed", "upcoming",)

class Youtube(object):
    """ 
    y2b sampleコードを抽象化
    """
    def __init__(self):
        self.lock = Lock()
        pass

    def __init_methods(self, flow=None, devkey=None):
      if devkey is not None:
          assert(flow is None)
          assert not isinstance(DEVELOPER_KEY, int), 'DEVELOPER_KEY not found.'
          self.auth_builder = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                                                          developerKey=DEVELOPER_KEY)
      else:
          asset(flow is not None)
          self.auth_builder = get_authenticated_service(flow)

    def __changeFlow(self, scope, message):
#        return flow_from_clientsecrets(CLIENT_SECRETS_FILE,
#                                    scope=YOUTUBE_UPLOAD_SCOPE,
#                                    message=MISSING_CLIENT_SECRETS_MESSAGE)
        assert scope in YOUTUBE_SCOPES.keys(), '%s is not registed YUTUBE_SCOPES you must select from %s'%(scope, YOUTUBE_SCOPES.keys())
        return flow_from_clientsecrets(CLIENT_SECRETS_FILE,
                                        scope=YOUTUBE_SCOPES[scope],
                                        message=message)

    def upload(self, file:str, title:str, desc:str, keywords:str, category=15, privacy=VALID_PRIVACY_STATUSES[0]):
        """
          argparser.add_argument("--auth", required=True, help="oauth clientfile")
          argparser.add_argument("--file", required=True, help="Video file to upload")
          argparser.add_argument("--title", help="Video title", default="Test Title")
          argparser.add_argument("--description", help="Video description",
            default="Test Description")
          argparser.add_argument("--category", default="15",
            help="Numeric video category. " +
              "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
          argparser.add_argument("--keywords", help="Video keywords, comma separated",
                default="")
          argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
                default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
        """
        with self.lock:
            flow = self.__changeFlow('UPLOAD', MISSING_CLIENT_SECRETS_MESSAGE)
            self.__init_methods(flow)
            try:
                class Dummy(object):
                    pass
                args = Dummy()
                args.auth, args.file, args.description, args.category = auth, file, desc, category
                args.keywords, args.privacyStatus= keywords, privacy
                initialize_upload(self.auth_builder, args)
            except HttpError as e:
                print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
        pass

    def list_broadcast(self, status=VALID_BROADCAST_STATUSES[0]):
        """
          if __name__ == "__main__":
              argparser.add_argument("--broadcast-status", help="Broadcast status",
                        choices=VALID_BROADCAST_STATUSES, default=VALID_BROADCAST_STATUSES[0])
              args = argparser.parse_args()

              youtube = get_authenticated_service(args)
              try:
                  list_broadcasts(youtube, args.broadcast_status)
              except HttpError, e:
                  print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
        """
        with self.lock:
            flow = self.__changeFlow('READONLY', MISSING_CLIENT_SECRETS_MESSAGE)
            self.__init_methods(flow)
            try:
                list_broadcasts(self.auth_builder, status)
            except HttpError as e:
                print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
        pass

    def getTokageCamLiveInfo(self, query='', max_results=25):
        """
        if __name__ == "__main__":
          argparser.add_argument("--q", help="Search term", default="Google")
          argparser.add_argument("--max-results", help="Max results", default=25)
          args = argparser.parse_args()

          try:
            youtube_search(args)
          except HttpError, e:
            print "An HTTP error %d occurred:\n%s" % (e.resp.status, e.content) 
        """
        with self.lock:
            self.__init_methods(devkey=DEVELOPER_KEY)
            try:
                search_response = self.auth_builder.search().list(
                                      q=query,
                                      part="id,snippet",
                                      order='date',
                                      eventType='live',
                                      type='video',
                                      channelId='UCnSINs9ZtrTz0caiI68NJNg',
                                      maxResults=max_results
                                  ).execute()
                # Add each result to the appropriate list, and then display the lists of
                # matching videos, channels, and playlists.
                return search_response.get("items", [])
            except HttpError as e:
                print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))

    def getTokageCamShortURL(self):
        items = self.getTokageCamLiveInfo()
        if len(items) > 0:
            vid = items[0]['id']['videoId']
            return shrot_url%vid
        else:
            return ''
# {
#  "kind": "youtube#searchListResponse",
#  "etag": "\"m2yskBQFythfE4irbTIeOgYYfBU/KaoMGAdxmSSjH1YmYbwYswK0Jzs\"",
#  "regionCode": "JP",
#  "pageInfo": {
#   "totalResults": 1,
#   "resultsPerPage": 5
#  },
#  "items": [
#   {
#    "kind": "youtube#searchResult",
#    "etag": "\"m2yskBQFythfE4irbTIeOgYYfBU/YeyBpS4J3jKitExVf1v-vI6wKxw\"",
#    "id": {
#     "kind": "youtube#video",
#     "videoId": "jMIvv51Ck5Y"
#    },
#    "snippet": {
#     "publishedAt": "2017-06-20T00:34:21.000Z",
#     "channelId": "UCnSINs9ZtrTz0caiI68NJNg",
#     "title": "TokageCamera Lifelog Archiver",
#     "description": "TokageCam -- Gecko activity analyze System construction-- トカゲ活動分析システム構築 more detail data https://www.setminami.net/TokageCam and tweeted ...",
#     "thumbnails": {
#      "default": {
#       "url": "https://i.ytimg.com/vi/jMIvv51Ck5Y/default_live.jpg",
#       "width": 120,
#       "height": 90
#      },
#      "medium": {
#       "url": "https://i.ytimg.com/vi/jMIvv51Ck5Y/mqdefault_live.jpg",
#       "width": 320,
#       "height": 180
#      },
#      "high": {
#       "url": "https://i.ytimg.com/vi/jMIvv51Ck5Y/hqdefault_live.jpg",
#       "width": 480,
#       "height": 360
#      }
#     },
#     "channelTitle": "Tokage Camera",
#     "liveBroadcastContent": "live"
#    }
#   }
#  ]
# }
# 


def get_authenticated_service(flow):
    storage = Storage(os.path.join(os.environ['HOME'], '.OAUTH/y2b-oauth2.json'))
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                        http=credentials.authorize(httplib2.Http()))

""" Youtube samples """
# Upload
def initialize_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body=dict(
            snippet=dict(
                          title=options.title,
                          description=options.description,
                          tags=tags,
                          categoryId=options.category
                ),
            status=dict(
                  privacyStatus=options.privacyStatus
            )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
          part=",".join(list(body.keys())),
          body=body,
          # The chunksize parameter specifies the size of each chunk of data, in
          # bytes, that will be uploaded at a time. Set a higher value for
          # reliable connections as fewer chunks lead to faster uploads. Set a lower
          # value for better recovery on less reliable connections.
          #
          # Setting "chunksize" equal to -1 in the code below means that the entire
          # file will be uploaded in a single HTTP request. (If the upload fails,
          # it will still be retried where it left off.) This is usually a best
          # practice, but if you're using Python older than 2.6 or if you're
          # running on App Engine, you should set the chunksize to something like
          # 1024 * 1024 (1 megabyte).
          media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if 'id' in response:
                print("Video id '%s' was successfully uploaded." % response['id'])
            else:
                exit("The upload failed with an unexpected response: %s" % response)
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                           e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                exit("No longer attempting to retry.")

        max_sleep = 2 ** retry
        sleep_seconds = random.random() * max_sleep
        print("Sleeping %f seconds and then retrying..." % sleep_seconds)
        time.sleep(sleep_seconds)

""" list """
# Retrieve a list of broadcasts with the specified status.
def list_broadcasts(youtube, broadcast_status):
    print("Broadcasts with status '%s':" % broadcast_status)

    list_broadcasts_request = youtube.liveBroadcasts().list(
        broadcastStatus=broadcast_status,
        part="id,snippet",
        maxResults=50
    )

    while list_broadcasts_request:
        list_broadcasts_response = list_broadcasts_request.execute()

        for broadcast in list_broadcasts_response.get("items", []):
            print("%s (%s)" % (broadcast["snippet"]["title"], broadcast["id"]))

        list_broadcasts_request = youtube.liveBroadcasts().list_next(
                                    list_broadcasts_request, list_broadcasts_response)

""" Search.list """
def youtube_search(options, search_list):

    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                                          developerKey=DEVELOPER_KEY)

    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = youtube.search().list(
                                  q=options.q,
                                  part="id,snippet",
                                  order='date',
                                  eventType='live',
                                  type='video',
                                  channelId='UCnSINs9ZtrTz0caiI68NJNg',
                                  maxResults=options.max_results
                                ).execute() 

    videos = []
    channels = []
    playlists = []

    # Add each result to the appropriate list, and then display the lists of
    # matching videos, channels, and playlists.
    for search_result in search_response.get("items", []):
        if search_result["id"]["kind"] == "youtube#video":
            videos.append("%s (%s)" % (search_result["snippet"]["title"],
                                         search_result["id"]["videoId"]))
        elif search_result["id"]["kind"] == "youtube#channel":
            channels.append("%s (%s)" % (search_result["snippet"]["title"],
                                           search_result["id"]["channelId"]))
        elif search_result["id"]["kind"] == "youtube#playlist":
            playlists.append("%s (%s)" % (search_result["snippet"]["title"],
                                            search_result["id"]["playlistId"]))

    print('Videos:\n%s'%'\n'.join(videos))
    print('Channels:\n%s'%"\n".join(channels))
    print('Playlists:\n%s'%"\n".join(playlists))



