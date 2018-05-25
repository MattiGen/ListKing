function checkAns(userInput, usrAns,answers){
    for (let i=0; i<answers.length; i+=1){
        if (userInput===answers[i]&&!usrAns.includes(userInput)){
            return 1;
        }

    }
    return 0;
}



///Everything below is just testing the modules, put this in a script tag, call line 21 on button press to
///submit answer

/*player={
    score:0,
    ans:[]
};

answers=['a','b','f'];

player.score+=(checkAns('f',player.ans,answers));
player.ans.push('f')

console.log(player.score);
console.log(player.ans);*/

