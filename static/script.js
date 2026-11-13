let timeout = 1000;
let lastId = 0; //let us get history on first fetch

function setup() {
    document.getElementById("messageForm").addEventListener("submit", makePost);
    poller();
}

function makePost(event) {
    event.preventDefault();
    const text = document.getElementById("messageText").value.trim();
    if (!text) {
        return;
    }

    fetch(messagesUrl, {
            method: "post",
            headers: { "Content-type": "application/json" },
            body: JSON.stringify({ "text": text })
        })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Could not post message!");
            }
            clearInput();
        })
        .catch(() => {
            console.log("Error posting message!");
        });
}

function poller() {
    fetch(messagesUrl + "?after=" + lastId)
        .then((response) => {
            if (response.status === 404) {
                window.location.href = chatroomsUrl + "?deleted=1";
                return null;
            }
            if (response.status === 401) {
                window.location.href = loginUrl;
                return null;
            }
            if (response.status === 403) {
                window.location.href = chatroomsUrl;
                return null;
            }
            if (!response.ok) {
                throw new Error("Could not fetch messages!");
            }
            return response.json();
        })
        .then((result) => {
            if (result !== null) {
                updateMessages(result);
            }
        })
        .catch(() => {
            console.log("Error fetching messages!");
            window.setTimeout(poller, timeout);
        });
}

function updateMessages(result) {
    for (let i = 0; i < result.messages.length; i++) {
        addMessage(result.messages[i]);
        lastId = result.messages[i].id;
    }

    window.setTimeout(poller, timeout);
}

function addMessage(message) {
    document.getElementById("noMessages").hidden = true;

    const item = document.createElement("li");
    const name = document.createElement("strong");
    name.appendChild(document.createTextNode(message.username));
    item.appendChild(name);
    item.appendChild(document.createTextNode(": " + message.text));
    document.getElementById("messages").appendChild(item);
}

function clearInput() {
    document.getElementById("messageText").value = "";
}

window.addEventListener("load", setup);
