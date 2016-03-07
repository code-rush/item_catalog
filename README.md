# Restaurant Menu App

### Steps to run the application on local machine
1) First of all you will need to download vagrant and virtual box on you computer and clone this repository https://github.com/udacity/fullstack-nanodegree-vm.

2) Fire up the terminal and navigate to the vagrant directory.

3) Excute following commands one at a time.

    vagrant up
    vagrant ssh
    
This will set the virtual environment for you application.
Once you ssh into vagrant, it means your virtual enivronment is set up and run the application in this environment.

4) Clone this item_catalog repository inside catalog folder inside vagrant.

5) After you ssh into vagrant, navigate to the item_catalog inside catalog folder. See the command below:

    cd /vagrant/catalog/item_catalog

6) Excute the following command, if you are running the application for the first time. This will install a Cross Site Request Forgery module that is needed for the application.

    sudo pip install flask-seasurf
    
7) Now start the application by executing the following command

    python runserver.py
    
8) Fire up a browser and go to http://localhost:5000/

You are successfully running the application on your local machine.

### To populate the database with items, follow the steps(This is only if you are running the application for the first time)

1) Copy database_setup.py from the folder item_catalog where it sits to the parent folder item_catalog which is inside catalog folder besides runserver.py.

2) In your terminal, press ctrl + c to stop running the application.

2) Execute python lotsofmenuwithusers.py and you will see the message "menu items added". This means you have successfully populated the database. Now you will be able to see the items in the application. 

3) Run python runserver.py and enjoy the experience on the application.


# Application Experience
* The first page contains the restaurants and the information about it. So, if any description or extra information is given to the restaurant, when you hover over it, you will see the description below the restaurant name tile.
* You can get information about the all restaurants from three different API endpoints; JSON, XML and RSS.
* Inside each restaurant contains the list of menu items that belongs to it. You can get the information of each item as well as all the items in the restaurant from three different API endpoints like restaurants.
* You can log in using either google or facebook account.
* Once you are logged in, you can add, edit and delete the restaurants that you created and the items in it.
* Items can contain picture. Upload the picture for the item while editing or creating an item.
* If you delete a restaurant, the items all the information about the item(including the picture) inside the restaurants will get deleted.
* The menu page contains information about the creator of the restaurant.