import StarRatingComponent from '/pages/StarRating.js';

class SongControlPanel {
    constructor(audioPlayer, songCoverElement, songLabelElement, songRatingElement, songProgressElement, socket, playlistManager) {
        this.audioPlayer = audioPlayer;
        this.songCoverElement = songCoverElement;
        this.songLabelElement = songLabelElement;
        this.songRatingElement = songRatingElement;
        this.songProgressElement = songProgressElement;
        this.socket = socket;
        this.playlistManager = playlistManager;
        this.DEFAULT_COVER_IMAGE = "static/images/128x128.png";
        this.currentSongHash = null;
        this.currentSongScore = null;
        this.showSongRatingTimeout = null;
        this.starRatingComponent = null;

        this.setupEventListeners();
        this.setupRatingComponent();

        $("#prev_btn").click(()=>{ 
            this.previousSong();
        });
        $("#play_btn").click(()=>{
            this.togglePlay();
        });
        $("#next_btn").click(()=>{
            this.nextSong();
        });
    }

    setupEventListeners() {
        this.audioPlayer.addEventListener("timeupdate", () => this.updateProgressBar());
        this.songProgressElement.on("click", (event) => this.handleProgressBarClick(event));
    }

    setupRatingComponent() {
      const callback = (rating) => {
        this.setSongRating(rating);
      };
      this.starRatingComponent = new StarRatingComponent({callback: callback});
      let element = this.starRatingComponent.issueNewHtmlComponent({
        containerType: 'span',
        size:3, 
        isActive: true
      });
      this.songRatingElement.empty();
      this.songRatingElement.append(element);
      this.songRatingElement.mouseleave(() => this.showSongRating(this.currentSongScore));
    }

    updateProgressBar() {
        const currentTime = this.audioPlayer.currentTime;
        const duration = this.audioPlayer.duration;
        this.songProgressElement.val(duration > 0 ? ((currentTime + 0.25) / duration * 100) : 0);
        localStorage.setItem("music_page_song_play_time", currentTime);
        localStorage.setItem("music_page_song_hash", this.currentSongHash);
    }

    handleProgressBarClick(event) {
        const clickX = event.clientX - this.songProgressElement.get(0).getBoundingClientRect().left;
        const progressBarWidth = this.songProgressElement.get(0).clientWidth;
        const clickPercentage = (clickX / progressBarWidth) * 100;
        this.songProgressElement.val(clickPercentage);
        const audioDuration = this.audioPlayer.duration;
        this.audioPlayer.currentTime = (clickPercentage / 100) * audioDuration;
    }

    setSongRating(score) {
        this.currentSongScore = score;
        this.showSongRating(score);
        // this.socket.emit('emit_music_page_set_song_rating', { hash: this.currentSongHash, score: score });
    }

    showSongRating(score, onHover = false, isUserRating = true) {
        if (!onHover) {
            this.currentSongScore = score;
        }
        this.starRatingComponent.rating = score;
        this.starRatingComponent.updateAllContainers();

        if (this.showSongRatingTimeout) {
          clearTimeout(this.showSongRatingTimeout);
        }
        if (onHover === false)
            this.showSongRatingTimeout = setTimeout(() => this.showSongRating(this.currentSongScore, false, isUserRating), 500);
    }
    
    // updateSongInfo(song) {
    //     this.currentSongHash = song.hash;
    //     this.showSongRating(parseInt(song.user_rating) || parseInt(song.model_rating) || 0, false, song.user_rating != null);
    //     this.songLabelElement.text(`${song.artist} - ${song.title} | ${song.album}`);
    //     this.songCoverElement.attr("src", song.image || this.DEFAULT_COVER_IMAGE);
    // }

    updateButtons() {
        if (this.playlistManager.isPlaying) {
            $("#play_btn").find('i').removeClass('fa-play');
            $("#play_btn").find('i').addClass('fa-pause');
        } else {
            $("#play_btn").find('i').removeClass('fa-pause');
            $("#play_btn").find('i').addClass('fa-play');
        }
    }

    playSong() {
        this.playlistManager.playSong();
        this.updateButtons();
    }

    pauseSong() {
        this.playlistManager.pauseSong();
        this.updateButtons();
    }

    togglePlay() {
        if (this.playlistManager.isPlaying) {
            this.pauseSong();
        } else {
            this.playSong();
        }
    }

    nextSong() {
        this.playlistManager.nextSong();
    }

    previousSong() {
        this.playlistManager.previousSong();
    }
}

export default SongControlPanel;