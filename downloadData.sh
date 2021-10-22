#2016 election data
curl -O https://files.pushshift.io/reddit/comments/RC_2015-09.bz2;
curl -O https://files.pushshift.io/reddit/comments/RC_2015-10.bz2;
curl -O https://files.pushshift.io/reddit/comments/RC_2015-11.bz2;
curl -O https://files.pushshift.io/reddit/comments/RC_2015-12.bz2;
curl -O https://files.pushshift.io/reddit/comments/RC_2016-01.bz2;

#2017 data
curl -O https://files.pushshift.io/reddit/comments/RC_2017-06.bz2;
#2018 data
curl -O https://files.pushshift.io/reddit/comments/RC_2018-06.xz;
#2019 data
curl -O https://files.pushshift.io/reddit/comments/RC_2019-06.zst;
##2020 data
curl -O https://files.pushshift.io/reddit/comments/RC_2020-06.zst;
##2021 data
curl -O https://files.pushshift.io/reddit/comments/RC_2021-06.zst;

mkdir dataFiles
mkdir rawData
mkdir jsonFiles
mkdir processDataFiles

#Unzip to Datafiles
echo Unzipping Files!
cd dataFiles;
bzip2 -d ../*.bz2;
unxz ../*.xz;
cd ../;
echo You need to unzip the zst files yourself!

##Move raw data to other folder
echo Moving Files!
mv *.bz2 ./rawData;
mv *.xz ./rawData;
mv *.zst ./rawData;

echo Done!
