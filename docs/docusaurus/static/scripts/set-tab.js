(function () {
  const querystring = window.location.search
  if (!querystring) {
    return
  }
  // pull groupId from anchor text, which should be equivalent
  const groupId = window.location.hash.replace('#', '')

  const entries = querystring
    .slice(1)
    .split('&')
    .reduce((entries, str) => {
      const [key, value] = str.split('=').map((v) => decodeURIComponent(v))
      entries[key] = value
      return entries
    }, {})
  if (typeof entries.tab === 'string') {
    const tab = entries.tab
    window.localStorage.setItem(`docusaurus.tab.${groupId}`, tab)
  }
})()

function scrollToHeading () {
  try {
    const heading = document.querySelector(window.location.hash)
    if (heading) {
      heading.scrollIntoView()
    }
  } catch (e) {
    // Sphinx anchor IDs (e.g. #module.Class.method) are invalid CSS selectors;
    // fall back to getElementById which accepts bare IDs without CSS escaping.
    const id = window.location.hash.slice(1)
    const heading = document.getElementById(id)
    if (heading) {
      heading.scrollIntoView()
    }
  }
}

window.onload = () => window.location.hash && scrollToHeading()
