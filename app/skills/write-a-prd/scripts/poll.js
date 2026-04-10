(function () {
  var contentEl = document.getElementById("content");
  var lastHtml = "";

  function poll() {
    fetch("/content")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.html && data.html !== lastHtml) {
          lastHtml = data.html;
          contentEl.style.opacity = "0";
          setTimeout(function () {
            contentEl.innerHTML = data.html;
            contentEl.style.opacity = "1";
          }, 80);
        }
      })
      .catch(function () {});
  }

  setInterval(poll, 2000);
  poll();
})();
