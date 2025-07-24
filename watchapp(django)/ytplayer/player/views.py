import re
from urllib.parse import unquote
import requests
import yt_dlp
from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt


def index(request):
    video_id = request.GET.get('v', '')
    if video_id:
        return redirect(f'/watch/?v={video_id}')
    return redirect('/watch/')


def watch_page(request):
    return render(request, 'watch.html')


@csrf_exempt
def get_stream_data(request, video_id):
    try:
        stream_data = extract_all_stream_info(video_id)
        return JsonResponse(stream_data)
    except Exception as e:
        print(f"Error extracting stream info for {video_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def proxy_stream(request, url):
    decoded_url = unquote(url)
    range_header = request.META.get('HTTP_RANGE', 'bytes=0-')
    headers = {'Range': range_header}

    try:
        resp = requests.get(decoded_url, headers=headers, stream=True)
        content_type = resp.headers.get('Content-Type', 'application/octet-stream')
        response = StreamingHttpResponse(
            resp.iter_content(chunk_size=1024 * 1024),
            content_type=content_type,
            status=resp.status_code,
        )
        if 'Content-Range' in resp.headers:
            response['Content-Range'] = resp.headers['Content-Range']
        return response
    except requests.exceptions.RequestException as e:
        print(f"Failed to proxy request: {e}")
        return StreamingHttpResponse(status=502)


def extract_all_stream_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_streams = [
            f for f in info['formats']
            if f.get('vcodec') != 'none'
               and f.get('acodec') == 'none'
               and f.get('ext') == 'mp4'
               and f.get('protocol') in ['http', 'https']
        ]
        audio_streams = [f for f in info['formats'] if
                         f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('ext') == 'm4a']
        audio_streams.sort(key=lambda f: f.get('abr', 0), reverse=True)
        if not audio_streams:
            raise Exception("Could not find a suitable audio stream.")
        best_audio = audio_streams[0]
        audio_mime = f'audio/mp4; codecs="{best_audio.get("acodec")}"'
        qualities = []
        added_heights = set()
        video_streams.sort(key=lambda f: f.get('height', 0), reverse=True)
        for stream in video_streams:
            height = stream.get('height')
            if height and height not in added_heights:
                qualities.append({
                    "height": height,
                    "label": f"{height}p",
                    "url": stream.get('url'),
                    "mime_type": f'video/mp4; codecs="{stream.get("vcodec")}"'
                })
                added_heights.add(height)
        if not qualities:
            raise Exception("Could not find any suitable progressive MP4 video streams.")
        return {
            'title': info.get('title', 'Unknown Title'),
            'duration': info.get('duration'),
            'audio_url': best_audio.get('url'),
            'audio_mime_type': audio_mime,
            'qualities': qualities
        }