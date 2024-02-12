async function callApi() {
    try {
        let token = ""
        let meeting_id = generateUUID();
        let url = `ws://localhost:8000/transcribe?meeting_id=${meeting_id}&token=${token}`
        let sock = new WebSocket(url)
        sock.onopen = () => {
                document.querySelector('#status').textContent = 'Connected'

                console.log({
                    event: 'onopen'
                })

                mediaRecorder.addEventListener('dataavailable', async (event) => {
                    if (event.data.size > 0 && socket.readyState == 1) {
                        socket.send(event.data)
                    }
                })
                mediaRecorder.start(250)
            }

//        window.location.href = url
    } catch (error) {
        console.error('Error calling API:', error);
    }
}

function generateUUID() { // Public Domain/MIT
    var d = new Date().getTime();//Timestamp
    var d2 = ((typeof performance !== 'undefined') && performance.now && (performance.now()*1000)) || 0;//Time in microseconds since page-load or 0 if unsupported
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16;//random number between 0 and 16
        if(d > 0){//Use timestamp until depleted
            r = (d + r)%16 | 0;
            d = Math.floor(d/16);
        } else {//Use microseconds since page-load if supported
            r = (d2 + r)%16 | 0;
            d2 = Math.floor(d2/16);
        }
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

