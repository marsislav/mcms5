#from django.http import HttpResponse
from django.shortcuts import render
def homepage (request):
    #return HttpResponse("Hello home")
    return render (request, 'home.html')
def about (request):
  #  return HttpResponse("Hello about")
  return render (request, 'about.html')