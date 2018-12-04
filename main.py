from __future__ import print_function, division
import math
import argparse
import pandas as pd
import constraint as solver
import openpyxl 
import numpy


# ------------ Constants --------- #

HOURS_IN_DAY = 8
WEEK_HOURS = HOURS_IN_DAY * 5
SLOT_DURATION = 2
CLASSROOM_SLOTS = WEEK_HOURS // SLOT_DURATION
MAX_CAPACITY=10000

# ------------- I/O -------------- #


#Simple reading of input file into all the different sections of dataframe
def parse(filename):
    df_classrooms = pd.read_excel(filename, "Classrooms")
    df_fixed_initial = pd.read_excel(filename, "Fixed and Placed")
    df_classes = pd.read_excel(filename, "Classes")
    df_groups = pd.read_excel(filename, "Groups")
    df_unavailable = pd.read_excel(filename, "Unavailable")
    df_unwanted = pd.read_excel(filename, "Unwanted")
    #required some formatin of data in order to be useable for my purposes and optimization
    df_fixed_initial=df_fixed_initial.fillna(value='Fake M1')
    df_unavailable=df_unavailable.fillna(value="S9")
    df_unwanted=df_unwanted.fillna(value="S9")
    df_classrooms=df_classrooms.sort_values("capacity")
    df_classrooms.index = range(0,len(df_classrooms))
    return df_classrooms, df_fixed_initial, df_classes, df_groups, df_unavailable, df_unwanted


#longest function in the file A LOT OF FORMATING but besides that not much to it
#TODO: Registar needs to be added
def write_results(placement, placement2, filename,df_classrooms, df_labrooms, df_classes):
    index=list(range(1,HOURS_IN_DAY+1))
    columns=['M', 'T', 'W','Th','F']
    df_ = pd.DataFrame(index=index, columns=columns)
    df_ = df_.fillna(0) # with 0s rather than NaNs
    df = pd.DataFrame.from_dict(placement, 'index')
    df_labs=pd.DataFrame.from_dict(placement2, 'index')
    length_labs=len(df_labrooms)
    
    length=len(df_classrooms)
    df_.to_excel(filename, sheet_name=df_classrooms['name'].iloc[0])
    book = openpyxl.load_workbook(filename)
    writer = pd.ExcelWriter(filename, engine='openpyxl') 
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
   
    df_total = pd.DataFrame(columns=columns)
    df_['M']=''
    df_['T']=''
    df_['W']=''
    df_['Th']=''
    df_['F']=''
    for j in range(length):
        temp=df.groupby(0).filter(lambda x: x.sum() > CLASSROOM_SLOTS*j )
        temp=temp.groupby(0).filter(lambda x: x.sum() <= CLASSROOM_SLOTS*(j+1) )
        for k in range(len(temp)):
            index=temp[0].iloc[k]-j*CLASSROOM_SLOTS
            slot, day= change_index_to_day(index)
            classname=temp[temp[0]==temp.iloc[k,0]].index.tolist()[0][0]
            part=temp[temp[0]==temp.iloc[k,0]].index.tolist()[0][1]
            time=df_classes[ classname == df_classes["name"] ].duration.iloc[0]
            if part==0:
                df_.iloc[slot*SLOT_DURATION,day]=classname
                if time>1:
                    df_.iloc[slot*SLOT_DURATION+1,day]=classname
            if part==1:
                df_.iloc[slot*SLOT_DURATION,day]=classname
                if time>3:
                    df_.iloc[slot*SLOT_DURATION+1,day]=classname  
        df_total=df_total.append(df_, ignore_index=True)
        df_.to_excel(writer,df_classrooms['name'].iloc[j] )
        writer.save()
        df_['M']=''
        df_['T']=''
        df_['W']=''
        df_['Th']=''
        df_['F']=''
    for j in range(length_labs):
        temp=df_labs.groupby(0).filter(lambda x: x.sum() > CLASSROOM_SLOTS*j )
        temp=temp.groupby(0).filter(lambda x: x.sum() <= CLASSROOM_SLOTS*(j+1) )
        for k in range(len(temp)):
            index=temp[0].iloc[k]-j*CLASSROOM_SLOTS
            slot, day= change_index_to_day(index)
            labname=temp[temp[0]==temp.iloc[k,0]].index.tolist()[0][0]
            section=temp[temp[0]==temp.iloc[k,0]].index.tolist()[0][1]
            part=temp[temp[0]==temp.iloc[k,0]].index.tolist()[0][2]
            time=df_classes[ labname == df_classes["name"] ].LabDuration.iloc[0]
            x=str(labname)+' '+str(df_labrooms['name'].iloc[j])+' '+'section:'+str(section)
            if part==0:
                df_.iloc[slot*SLOT_DURATION,day]=x
                if time>1:
                    df_.iloc[slot*SLOT_DURATION+1,day]=x
            if part==1:
                df_.iloc[slot*SLOT_DURATION,day]=x
                if time>3:
                    df_.iloc[slot*SLOT_DURATION+1,day]=x
        df_total=df_total.append(df_, ignore_index=True)
        df_['M']=''
        df_['T']=''
        df_['W']=''
        df_['Th']=''
        df_['F']=''
    index2=[]
    index=list(range(1,HOURS_IN_DAY+1))*(len(df_classrooms)+len(df_labrooms))
    for a in range(len(df_classrooms)):
        for b in range(1,HOURS_IN_DAY+1):
            c=df_classrooms['name'].iloc[a]
            index2.append(str(b)+' '+c)
    for a in range(len(df_labrooms)):
        for b in range(1,HOURS_IN_DAY+1):
            c=df_labrooms['name'].iloc[a]
            index2.append(str(b)+' '+c)
    df_total.index=index
    
    df_total['classrooms'] = pd.Series(index2, index=df_total.index)
    df_total.sort(['classrooms'], ascending=[True], inplace=True)
    df_total.to_excel(writer,'Allclasses')
    writer.save()

        
     


# ------------ Helpers ------------ #

# Most of the function names explain exactly what they do this is the portion
# Where I had to use math to go between the domain index and days and slots of human 
# Readable formats


def change_index_to_day(index):
    #Days go from 0-4 
    index=index-1
    day=int(index/(HOURS_IN_DAY/SLOT_DURATION+0.0))
    slot=int(index-day*(HOURS_IN_DAY/SLOT_DURATION))
    return slot, day

def get_all_slots(df_classrooms):
    """
    # Note about slots
    Slots are the time ranges in some classroom that we can assign it to a class.
    We count slots from first hours (slot) of the week to the last hours(slot) of the week for each class.
    After we count week of one class, we count week of next class and so on.
    For example, if we have 4 slots for one week for one classroom and if we have 3 classroom then slot numbers are:
    classroom1: 1 2 3 4
    classroom2: 5 6 7 8
    classroom3: 9 10 11 12
    where slots for each class are ordered by time
    """
    max_slot_number = len(df_classrooms) * CLASSROOM_SLOTS
    return set(range(1, max_slot_number + 1))
    
    
def slots_of_labs(lab_name, df_labs):
    """
    # Note about slots_of_labs
    
    This function is used twice one for classes and one for labs the reason for
    Duplicates is because there may be different numbers of labs and classrooms which
    Would mess up everything for us if not careful
    
    """
    length=len(df_labs)
    for k in range(length):
        if df_labs.iloc[k,0]==lab_name:
            order_of_lab=k+1    
    last_slot_of_prev_lab = (order_of_lab - 1) * CLASSROOM_SLOTS
    first_slot_of_next_lab = order_of_lab * CLASSROOM_SLOTS + 1
    return set(range(last_slot_of_prev_lab + 1, first_slot_of_next_lab))
    
    
    
def slots_of_specificslot(tot, df_classrooms):
    """
    # Note about slots_specficslot
    
    This function is used for the sheet of set classes, this is because since those classes
    Also have set classrooms we need this function as a seperate function
    
    """
    x=tot.split()
    classroom=x[0]
    if classroom=='Fake':
        return 123123
    order_of_classroom = df_classrooms[df_classrooms["name"] == classroom].index.item()
    time=x[1]
    hour=time[-1]
    day=time[0:-1]
    if day== 'M':
        day=0
    if day== 'T':
        day=1
    if day== 'W':
        day=2
    if day== 'Th':
        day=3
    if day=='F':
        day=4
    index=day*HOURS_IN_DAY/SLOT_DURATION+math.ceil(int(hour)/(SLOT_DURATION+0.0))
    index=index+ order_of_classroom*CLASSROOM_SLOTS
    return int(index)
    
    
def slots_of_classroom(classroom_name, df_classrooms):
    #much like the other function
    order_of_classroom = df_classrooms[df_classrooms["name"] == classroom_name].index.item() + 1
    first_slot_of_prev_classroom = (order_of_classroom - 1) * CLASSROOM_SLOTS
    last_slot_of_next_classroom = order_of_classroom * CLASSROOM_SLOTS + 1
    return set(range(first_slot_of_prev_classroom + 1, last_slot_of_next_classroom))


def slots_of_time(time, df_classrooms):
    #much like specific slots function but without the classroom being set
    hour=time[-1]
    day=time[0:-1]
    if day=='S':
        return {123123}
    if day== 'M':
        day=0
    if day== 'T':
        day=1
    if day== 'W':
        day=2
    if day== 'Th':
        day=3
    if day=='F':
        day=4
    index=day*HOURS_IN_DAY/SLOT_DURATION+math.ceil(int(hour)/(SLOT_DURATION+0.0))
    a=set()
    for i in range(len(df_classrooms)):
        a.add(i*CLASSROOM_SLOTS+index)
    return a

def slots_of_time_toindex(slot,day, df_labs):
    #this function is the reverse of the first function.
    index=day*HOURS_IN_DAY/SLOT_DURATION+math.ceil(int(slot))
    a=set()
    for i in range(len(df_labs)):
        a.add(i*CLASSROOM_SLOTS+index)
    return a
    
#function to delete time slots before a given time slot  
def after_time(slot, day, df_labs):
    a=set()
    for day_ in range(5):
        for slot_ in range(int(HOURS_IN_DAY/SLOT_DURATION)):
            if day_<day or (day_==day and slot_<=slot):
                a=a | slots_of_time_toindex(slot_,day_, df_labs)
    return a


def add_professor_groups(df_classes, df_groups):
    """
    # Note about add_professor_groups
    
    This function is not like the other helpers, this function is used for the groups constraint
    For unique classes new groups are added to df_groups so that proffesors giving more than 
    One class do not have classes at the same time
    
    """    
    i = 0
    for prof_name in df_classes.ProfessorName.unique():
        i += 1
        group_name="professor_group"+str(i)
        prof_classes=df_classes[ prof_name == df_classes["ProfessorName"] ]
        if len(prof_classes)>1:
            for class_name in prof_classes.name:
                df_groups=df_groups.append({"Groupnames":group_name, "Class":class_name}, ignore_index=True)
    return df_groups


# ------------------ Domains ------------------ #

#function to get the initial domains for each class and according to their duration
#the amount of parts it will have, very similar to lab_domains function
def init_domains(df_classes, initial_domain):
    domains = {}
    for idx, class_name, professor_name, number_of_students, duration, ps,lab_section,lab_duration,lab_place in df_classes.itertuples():
        # divide classes to parts if they don't fit inside one slot
        for part_number in range(int(math.ceil(duration / SLOT_DURATION))):
            domains[(class_name, part_number)] = initial_domain.copy()
    return domains

def init_domains_labs(df_classes, initial_domain):
    domains = {}
    for idx, class_name, professor_name, number_of_students, duration, ps,lab_section,lab_duration,lab_place in df_classes.itertuples():
        # divide classes to parts if they don't fit inside one slot
        for duray in range(int(math.ceil(lab_duration / SLOT_DURATION))):
            for part_number in range(lab_section):
                domains[(class_name, part_number, duray)] = initial_domain.copy()
    return domains
    
#Hard set constraint of deleting by hard set placement, WARNING!!!! THIS FUNCTION IS PRONE TO ERROR
# WHILE USING THIS PLEASE MAKE SURE YOU ARE NOT MAKING IMPOSSIBLE INPUTS BASED ON 
#1)CAPACITY 
#2)DURATION OF CLASS BEING CORRECT
#3)CORRECT SPELLING OF CLASSROOM
#4)HARD SET PROFESSOR RESTRICTIONS NOT BEING AT ODDS WITH PLACEMENT
# IF NOT CORRECTLY APPLIED HAS CONSEQUENCES SUCH AS INFINITE LOOPS
    
def eliminate_by_placement(domains, df_fixed_initial):
    df_fixed_initial.fillna(value='Fake M1')
    for (class_name, part), domain in domains.items():
       k=df_fixed_initial[df_fixed_initial['classes']==class_name]
       setdomains=set()
       if len(k)==0:
           continue
       c=0
       for z in k:
           if z!="classes" and z!='Registar':
               setdomains.add(slots_of_specificslot(k.iloc[0,c], df_classrooms))
               setdomains.discard(123123)
           c=c+1
       domains[(class_name, part)]=setdomains.copy()
    return domains


#Hard set constraint of deleting by the amount of students that can fit into a classroom, 
#This sometimes is the reason for new classrooms needing to be opened up
def eliminate_by_capacity(domains, df_classrooms, df_classes):
    for (class_name, part), domain in domains.items():
        number_of_students = df_classes[df_classes["name"] == class_name].numberofstudents.item()
        # for each classroom that don't have enough capacity for number of students of a class
        for classroom_name in df_classrooms[number_of_students > df_classrooms["capacity"]].name:
            # eliminate slots of these classrooms
            domains[(class_name, part)] -= slots_of_classroom(classroom_name, df_classrooms)
    return domains

# Eliminate according to classes from registar
def eliminate_by_registration(domains,df_groups,df_registar):
    for (class_name, part), domain in domains.items():
        for group_name in df_groups[ class_name == df_groups["Class"] ].Groupnames:
            for a in df_groups[ group_name == df_groups["Groupnames"] ].Class:
                if a!=class_name:
                    b=df_registar[ df_registar["classes"]==a ]
                    if len(b)==0:
                        continue
                    c=0                    
                    for z in b:
                        if z!="classes" and z!='Registar':
                            domains[(class_name, part)] -= slots_of_time(b.iloc[0,c], df_classrooms)
                        c=c+1
    return domains
    

#Ellimanation function for unwanted and unavaible days both hard and soft use the same function
def eliminate_by_professor_availability(domains,df_classes, df_restrictions):
    for (class_name, part), domain in domains.items():
        for prof_name in df_classes[ class_name == df_classes["name"] ].ProfessorName :
            for a in df_classes[ prof_name == df_classes["ProfessorName"] ].name:
                    b=df_restrictions[ df_restrictions["Professor"]==prof_name ]
                    if len(b)==0:
                        continue
                    c=0 
                    for z in b:
                        if z!="Professor":
                            domains[(class_name, part)] -= slots_of_time(b.iloc[0,c], df_classrooms)
                        c=c+1
    return domains

#Elimination function for both hard and set professor needs 
def eliminate_by_fixed(domains, df_groups,df_classrooms, df_fixed_initial):
            df1=df_fixed_initial.loc[df_fixed_initial.Registar==0]
            df2=df_fixed_initial.loc[df_fixed_initial.Registar==1]
            domains= eliminate_by_registration(domains,df_groups, df2)
            domains= eliminate_by_placement(domains, df1)
            return domains

#elimination function for labplaces, since the lab places have set labs this restricts the domain by a lot
def eliminate_by_labplace(df_labs ,df_classes_withlabs,domains2):
    for (class_name, section, part), domain in domains2.items():
        lab_name = df_classes_withlabs[df_classes_withlabs["name"] == class_name].LabPlace.item()
        domains2[(class_name, section, part)] = slots_of_labs(lab_name, df_labs).copy()
    return domains2
    
#restrictions for lab domains   
def restrict_lab_domains(df_labs, df_classes_withlabs, domains2,placement):
    domains2=eliminate_by_labplace(df_labs, df_classes_withlabs,domains2)
    domains2=eliminate_by_class(df_classes_withlabs,domains2,placement,df_labs)
    return domains2
    
    
#Elimination for the lab once again but this time elimantin of times before the lab section itself 
def eliminate_by_class(df_classes_withlabs,domains2,placement, df_labs):
    df = pd.DataFrame.from_dict(placement, 'index')
    length=len(df_classrooms)
    for j in range(length):
        temp=df.groupby(0).filter(lambda x: x.sum() > CLASSROOM_SLOTS*j )
        temp=temp.groupby(0).filter(lambda x: x.sum() <= CLASSROOM_SLOTS*(j+1) )
        for k in range(len(temp)):
            index=temp[0].iloc[k]-j*CLASSROOM_SLOTS
            slot, day= change_index_to_day(index)
            classname=temp[temp[0]==temp.iloc[k,0]].index.tolist()[0][0]
            for (dummy, part, duration) in domains2:
                if(dummy==classname):
                   domains2[(classname, part, duration)] -= after_time(slot, day, df_labs)
    return domains2

#full function for the restricted classes put together
def find_restricted_domains(df_classrooms, df_classes,df_groups, df_fixed_initial, df_unavailable, df_unwanted):
    full_domain = get_all_slots(df_classrooms)
    domains = init_domains(df_classes, full_domain)
    domains = eliminate_by_professor_availability(domains, df_classes, df_unavailable)
    domains = eliminate_by_professor_availability(domains, df_classes, df_unwanted)
    domains= eliminate_by_fixed(domains, df_groups,df_classrooms,df_fixed_initial)
    domains = eliminate_by_capacity(domains, df_classrooms, df_classes)
    return domains


# ----------------- Constraints --------------------- #


#This portion is for the dynamic part of the code, we need to get constraints
#in order to feed with the domains into the solver algorithm in order to solve the optimization problem

#group constraints function, creates a function for classes in the same groups
def group_constraint(*slots):
    mods=[slot%CLASSROOM_SLOTS for slot in slots]
    if len(mods) > len(set(mods)):
        return False
    return True
    
#part constraint this is for the same parts not being on the same day   
def part_constraint(part1,part2):
    slot1,day1=change_index_to_day(part1)
    slot2,day2=change_index_to_day(part2)
    if day1==day2:
        return False
    return True

#the function that generates group constraint function, so a function that creates functions
def generate_group_constraints(df_groups, domains):
    group_constraints = []
    for group in df_groups.Groupnames.unique():
        group_variables = []
        for class_name in df_groups[df_groups.Groupnames==group].Class:
            if class_name[0:2]!='ee':
                continue
            parts= [(class_name_temp, part) for (class_name_temp, part), domain in domains.items() 
                    if class_name==class_name_temp]
            group_variables.extend(parts)
        group_constraints.append((group_constraint, group_variables))
    return group_constraints
    
#function to create part functions   
def generate_part_constraints(domains):
    part_constraints = []
    for (class_name, part), domain in domains.items():
        if part>0:
            part_constraints.append((part_constraint, [(class_name, 0),(class_name, 1)]))
    return part_constraints


def define_constraints(df_groups, domains):
    constraints = []
    # Add contraints that are generated for each group
    constraints.extend(generate_group_constraints(df_groups, domains))
    constraints.extend(generate_part_constraints(domains))
    # Each slot can only be assigned to one variable
    constraints.append((solver.AllDifferentConstraint(),))
    return constraints


def define_lab_constraints(domains2):
    constraints2 = []
    # Each slot can only be assigned to one variable
    constraints2.append((solver.AllDifferentConstraint(),))
    return constraints2
    
    
# ----------------- Solver --------------------- #


def generate_solutions(domains, constraints):
    problem = solver.Problem()
    # Add variables and their domains
    try:
        for variable, domain in domains.items():
            problem.addVariable(variable, list(reversed(sorted(domain))))
    except ValueError:
            return
    # Add constraints
    for constraint in constraints:
        problem.addConstraint(*constraint)
    # return solution iterator
    try:
        return problem.getSolution()
    except RuntimeError:
        return

def generate_solutions_lab(domains2, constraints2):
    problem = solver.Problem()
    # Add variables and their domains
    for variable, domain in domains2.items():
        problem.addVariable(variable, list(domain))
    # Add constraints
    for constraint in constraints2:
        problem.addConstraint(*constraint)
    # return solution iterator
    return problem.getSolutionIter()
    
    
#-------------------------Constraint Lifters-----------------#
    
#while removing constraints from professors, we do this fairly by going in reversed maximum row order
def fair_distribution(df_unwanted):
    for constraintsno in reversed(range(1,len(df_unwanted.columns))):
        for row in df_unwanted[df_unwanted[constraintsno]!='S9'].iterrows() :
            yield row[1][0], row[1][int(constraintsno)]
    
    
    
    
#removing soft constraints 1by1   
def soften_constraints(domains, df_unwanted, df_classrooms, df_classes):
    yield domains
    #finding the class to put back into domain
    for prof_name,time in fair_distribution(df_unwanted):
        #classname is found
        for (class_name, part), domain in domains.items():
            #the professor matching is found
            for prof_name2 in df_classes[ class_name == df_classes["name"] ].ProfessorName :
                if(prof_name==prof_name2):
                    domains[(class_name, part)]=domains[(class_name, part)] | slots_of_time(time, df_classrooms)
                    #readded into domain
                    domains = eliminate_by_capacity(domains, df_classrooms, df_classes)
                    yield domains    

  
#last hope situation of adding a classroom with huge capacity  
def add_classroom(name, df_classrooms):
    df_classrooms=df_classrooms.append({'name': name, 'capacity':MAX_CAPACITY}, ignore_index=True)
    df_classrooms.index = range(0,len(df_classrooms))
    return df_classrooms.sort_values("capacity")
 

#required for initialization purposes   
def init_placement():

    return {}


#playing the labs down this is like the 2nd main function actually
def lab_placement(df_classes, df_groups,placement):
    columns=['name', 'capacity']
    df_labs = pd.DataFrame(index=None, columns=columns)
    for lab_name in df_classes.LabPlace.unique():
        if lab_name!=0:
            df_labs=df_labs.append({'name': lab_name, 'capacity':MAX_CAPACITY}, ignore_index=True)
    full_domain = get_all_slots(df_labs)
    df_classes_withlabs= df_classes[df_classes.LabPlace != 0]
    df_classes.drop
    domains2 = init_domains_labs(df_classes_withlabs, full_domain)
    domains2=restrict_lab_domains(df_labs, df_classes_withlabs, domains2, placement)
    
    return df_labs, domains2
    
# -------------------- Main ------------------------- #    
if __name__ == '__main__':
    # Parse commandline args
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    filename = parser.parse_args()

    # Parse excel file
    df_classrooms, df_fixed_initial, df_classes, df_groups, df_unavailable, df_unwanted = parse(filename.input)
    # Add groups from professors
    df_groups = add_professor_groups(df_classes, df_groups)
    
    #df_labs formation for check of if classroom==labroom
    #TODO FOR MIXED DOMAINS
    #for lab_name in df_classes.LabPlace.unique():
    #    if lab_name!=0:
    #        df_labs=df_labs.append({'name': lab_name, 'capacity':MAX_CAPACITY}, ignore_index=True)
    
    # Get domains that already restricted by some constraints
    domains = find_restricted_domains(df_classrooms, df_classes,df_groups, df_fixed_initial,df_unavailable, df_unwanted)
    
    # Get all constraints that is checked at each stage of the solver
    constraints = define_constraints(df_groups, domains)

    # Make initial placements for... TODO: explain shortly from func def
    initial_placement = init_placement()
    
    found=False
    count=0
    
    #we put it into a loop in order to solve the unsolution problems by removing soft constraints and
    #adding classes
    while(not found):
        #first try to remove soft constraints
        for domains in soften_constraints(domains, df_unwanted,df_classrooms, df_classes):
            #solution is created WARNING THERE IS A SMALL ERROR HERE MAKE SURE SOFT CONSTRAINTS ARE NOT IN HARD
            #CONSTRAINTS ALSO THIS WILL MAKE THE CODE HAVE ERRORS AND MESS UP 
            solution= generate_solutions(domains, constraints)
            if solution:
                placement = initial_placement.copy()
                placement.update(solution)
                found=True
                break 
        if found:
            break
        #if not found than we have to add a classroom and reinstate the softconstraints
        df_classrooms=add_classroom(str(count), df_classrooms) 
        print('here')
         
        #lastly we have to go through the restricted domains once more after the shuffle for 
        domains = find_restricted_domains(df_classrooms, df_classes,df_groups, df_fixed_initial,df_unavailable, df_unwanted)
        count+=1
    
    
    #Portion of code for labs
    df_labs, domains2=lab_placement(df_classes, df_groups,placement)
    constraints2= define_lab_constraints(domains2)
    initial_lab_placement = init_placement()
    for solution2 in generate_solutions_lab(domains2, constraints2):
        placement2 = initial_lab_placement.copy()
        placement2.update(solution2)
        break  
    
    #output results are printed
    write_results(placement, placement2, filename.output,df_classrooms,df_labs, df_classes)
