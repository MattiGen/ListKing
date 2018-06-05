function getRequests(url){
    let xhr = new XMLHttpRequest();
    xhr.responseType="json";
    xhr.onreadystatechange=function(){
        if (xhr.readyState===XMLHttpRequest.DONE){
            console.log(xhr.response);
            return xhr.response;
        }
    };
    xhr.open('GET',url);
    xhr.send();
}




function postRequest(data, url){
    let xhr = new  XMLHttpRequest();
    data=JSON.stringify(data);
    xhr.responseType="json";
    xhr.onreadystatechange=function(){
        if (xhr.readyState===XMLHttpRequest.DONE){
            console.log(xhr.response);
            return xhr.response;
        }
    };
    xhr.open('POST',url);
    xhr.send(data);
}