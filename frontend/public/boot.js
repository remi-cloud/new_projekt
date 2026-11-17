window.addEventListener('error', function () {
  var shell = document.getElementById('boot-shell');
  if (shell) {
    shell.innerHTML = '<strong>Cykliczny Trader</strong><span>Błąd ładowania — odśwież (Cmd+Shift+R)</span>';
  }
});
setTimeout(function () {
  var root = document.getElementById('root');
  var shell = document.getElementById('boot-shell');
  if (root && shell && root.contains(shell) && root.children.length === 1) {
    shell.innerHTML = '<strong>Cykliczny Trader</strong><span>Aplikacja nie wystartowała — twarde odświeżenie (Cmd+Shift+R)</span>';
  }
}, 8000);
