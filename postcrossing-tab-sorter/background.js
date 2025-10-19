async function sortPostcrossingTabs() {
  try {
    let tabs = await browser.tabs.query({ currentWindow: true });

    let postTabs = tabs.filter(tab =>
      tab.url.startsWith("https://www.postcrossing.com/postcards/")
    );

    if (postTabs.length === 0) {
      console.log("No PostCrossing tabs found in this window.");
      return;
    }

    postTabs.sort((a, b) => {
      const codeA = a.url.split("/postcards/")[1];
      const codeB = b.url.split("/postcards/")[1];

      if (!codeA || !codeB) return 0;

      const [countryA, numA] = codeA.split("-");
      const [countryB, numB] = codeB.split("-");

      if (countryA < countryB) return -1;
      if (countryA > countryB) return 1;
      return parseInt(numA) - parseInt(numB);
    });

    for (let i = 0; i < postTabs.length; i++) {
      await browser.tabs.move(postTabs[i].id, { index: i });
    }

    console.log(" PostCrossing tabs sorted successfully!");
  } catch (err) {
    console.error("Error sorting tabs:", err);
  }
}

browser.browserAction.onClicked.addListener(sortPostcrossingTabs);
