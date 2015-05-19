import webbrowser
import os
import re

# Styles and scripting for the page
main_page_head = '''
<head>
    <meta charset="utf-8">
    <title>List Flix - Yes a list of some quality flix</title>

    <!-- Bootstrap 3 -->
    <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/bootstrap/3.1.0/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/bootstrap/3.1.0/css/bootstrap-theme.min.css">
    <link href='http://fonts.googleapis.com/css?family=Cabin:400,600|Lobster' rel='stylesheet' type='text/css'>
    <script src="http://code.jquery.com/jquery-1.10.1.min.js"></script>
    <script src="https://netdna.bootstrapcdn.com/bootstrap/3.1.0/js/bootstrap.min.js"></script>
    <style type="text/css" media="screen">
        body {
            padding-top: 80px;
            background: url(images/binding_dark.png);
            font-family: 'Cabin', sans-serif;
        }
        #trailer .modal-dialog {
            margin-top: 200px;
            width: 640px;
            height: 480px;
        }
        .hanging-close {
            position: absolute;
            top: -12px;
            right: -12px;
            z-index: 9001;
        }
        #trailer-video {
            width: 100%;
            height: 100%;
        }
        .movie-tile {
            margin-bottom: 20px;
            padding-top: 20px;
        }
        .movie-tile:hover {
            background-color: #EEE;
            cursor: pointer;
        }
        .scale-media {
            padding-bottom: 56.25%;
            position: relative;
        }
        .scale-media iframe {
            border: none;
            height: 100%;
            position: absolute;
            width: 100%;
            left: 0;
            top: 0;
            background-color: white;
        }
        footer {
            height: 60px;
            text-align: center;
        }
        footer span {
            margin-right: 3em;
        }
        .navbar {
            background: url(images/stardust.png);
            opacity: .95;
            height: 70px;
        }
        .header-text {
            color: white !important;
            font-family: 'Lobster', cursive;
            font-size: 3em;
            padding: .5em;
        }
        .header-subtext {
            font-size: .5em;
        }
        .movie-frame {
            background: url(images/movie_frame.png);
            z-index: 2;
            width: 780px;
            height: 530px;
            background-size: contain;
            text-align: center;
        }
        .movie-frame h2 {
          margin-top: 1em;
          font-weight: 600;
          color: white;
        }
        .movie-frame img {
            display: inline-block;
            margin-top: 1em;
            margin-bottom: 1em;
            margin-right: 1em;
        }
        .movie-summary {
          display: inline-block;
          font-size: 1.2em !important;
          width: 45%;
          color: white;
        }
        .btn-trailer {
          display: inline-block;
          width: 50%;
          margin-top: 1em;
        }
    </style>
    <script type="text/javascript" charset="utf-8">
        // Pause the video when the modal is closed
        $(document).on('click', '.hanging-close, .modal-backdrop, .modal', function (event) {
            // Remove the src so the player itself gets removed, as this is the only
            // reliable way to ensure the video stops playing in IE
            $("#trailer-video-container").empty();
        });
        // Start playing the video whenever the trailer modal is opened
         $(document).on('click', '.btn-trailer', function (event) {
            var trailerYouTubeId = $('#trailer-video-container').attr('data-trailer-youtube-id');
            var sourceUrl = 'http://www.youtube.com/embed/' + trailerYouTubeId + '?autoplay=1&html5=1';
            $("#trailer-video-container").empty().append($("<iframe></iframe>", {
              'id': 'trailer-video',
              'type': 'text-html',
              'src': sourceUrl,
              'frameborder': 0
            }));
        });
        // load in contents of selected movie into jumbotron
        $(document).on('click', '.movie-tile', function (event) {
            var _movieFrame = $('.movie-frame');
            _movieFrame.find('.movie-summary').text($(this).attr('data-story'));
            _movieFrame.find('h2').text($(this).find('h2').text());
            _movieFrame.find('img').attr('src', $(this).find('img').attr('src'));
            $('#trailer-video-container').attr('data-trailer-youtube-id', $(this).attr('data-trailer-youtube-id'));
            // autoscroll to top
            $("html,body").animate({scrollTop: 0}, 300);

        });

        // Animate in the movies when the page loads
        $(document).ready(function () {
          $('.movie-tile').hide().first().show("fast", function showNext() {
            $(this).next("div").show("fast", showNext);
          });
          
        });
    </script>
</head>
'''

# The main page layout and title bar
main_page_content = '''
<!DOCTYPE html>
<html lang="en">
  <body>
    <!-- Trailer Video Modal -->
    <div class="modal" id="trailer">
      <div class="modal-dialog">
        <div class="modal-content">
          <a href="#" class="hanging-close" data-dismiss="modal" aria-hidden="true">
            <img src="https://lh5.ggpht.com/v4-628SilF0HtHuHdu5EzxD7WRqOrrTIDi_MhEG6_qkNtUK5Wg7KPkofp_VJoF7RS2LhxwEFCO1ICHZlc-o_=s0#w=24&h=24"/>
          </a>
          <div class="scale-media" id="trailer-video-container" data-trailer-youtube-id="u6Squ9a2kO4">
          </div>
        </div>
      </div>
    </div>
   
    <!-- Main Page Content -->
    <div class="container">
      <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
        <div class="container">
          <div class="navbar-header">
            <a class="navbar-brand header-text" href="#">ListFlix <small><span class='header-subtext'>quality lives here</span></small></a>
          </div>
        </div>
      </div>
    </div>
    <div class="container">
      <div class="jumbotron center-block movie-frame">
        <h2>Snakes on a Plane</h2>
        <img src="http://upload.wikimedia.org/wikipedia/en/4/41/SOAP_poster.jpg" width="150" height="240">
        <p class="movie-summary">A suspenseful tail about one man trying to save a planeful of passengers from a slitering, scaly set of intruders.</p>
        <p><a class="btn btn-primary btn-lg btn-trailer" href="#" role="button" data-toggle="modal" data-target="#trailer">trailer</a></p>
      </div>
      {movie_tiles}
    </div>
    <footer>
      <span>project by Andrew Roy Chen</span>
      <a href="https://github.com/uncleoptimus/FSND1-ListFlix">I'm on Github!</a>
    </footer>
  </body>
</html>
'''

# A single movie entry html template
movie_tile_content = '''
  <div class="col-md-6 col-lg-4 movie-tile text-center" data-trailer-youtube-id="{trailer_youtube_id}" data-story="{storyline}">
    <img src="{poster_image_url}" width="220" height="342">
    <h2>{movie_title}</h2>
</div>
'''

def create_movie_tiles_content(movies):
    # The HTML content for this section of the page
    content = ''
    for movie in movies:
        # Extract the youtube ID from the url
        youtube_id_match = re.search(r'(?<=v=)[^&#]+', movie.trailer_youtube_url)
        youtube_id_match = youtube_id_match or re.search(r'(?<=be/)[^&#]+', movie.trailer_youtube_url)
        trailer_youtube_id = youtube_id_match.group(0) if youtube_id_match else None

        # Append the tile for the movie with its content filled in
        content += movie_tile_content.format(
            movie_title=movie.title,
            poster_image_url=movie.poster_image_url,
            trailer_youtube_id=trailer_youtube_id,
            storyline=movie.storyline
        )
    return content

def open_movies_page(movies):
  # Create or overwrite the output file
  # output_file = open('fresh_tomatoes.html', 'w')

  # Replace the placeholder for the movie tiles with the actual dynamically generated content
  rendered_content = main_page_content.format(movie_tiles=create_movie_tiles_content(movies))

  # Output the file
  # output_file.write(main_page_head + rendered_content)
  # output_file.close()

  return main_page_head + rendered_content

  # open the output file in the browser
  # url = os.path.abspath(output_file.name)
  # webbrowser.open('file://' + url, new=2) # open in a new tab, if possible