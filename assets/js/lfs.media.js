function lfsmedia() {
    var media = document.getElementsByClassName("lfs");
    var lfs = "https://media.githubusercontent.com/media/tsutterley/tsutterley.github.io/main/";
    for (var i = 0; i < media.length; i++) {
        media[i].src = lfs + media[i].getAttribute('data-path') + "?raw=true";
    }
}
