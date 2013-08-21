// pyfunctions.h
// James Mithen
// j.mithen@surrey.ac.uk

// Declarations for functions to be called by Python via Boost.Python

#include <vector>
#include <boost/python.hpp>
#include "boost/python/extract.hpp"
#include "boost/python/numeric.hpp"
#include "constants.h"

double py_fracsolidld(boost::python::numeric::array,
							 boost::python::numeric::array,
							 boost::python::numeric::array, 
						    const int, const int, const double, const double,
							 const double, const bool, const double);
double py_fracsolidtf(boost::python::numeric::array,
							 boost::python::numeric::array,
							 boost::python::numeric::array, 
						    const int, const int, const double, const double,
							 const double, const bool, const double, const int,
							 const double);
double py_nclustf(boost::python::numeric::array,
						boost::python::numeric::array,
						boost::python::numeric::array, 
						const int, const int,
						const double, const double,
						const double, const bool, const double,
						const int, const double);
double py_nclusld(boost::python::numeric::array,
						boost::python::numeric::array,
						boost::python::numeric::array, 
						const int, const int, const double, const double,
						const double, const bool, const double);
std::vector<LDCLASS> py_ldclass(boost::python::numeric::array,
										  boost::python::numeric::array,
										  boost::python::numeric::array, 
										  const int, const int, const double, const double,
										  const double, const bool, const double);

// structs used to convert from C++ types to python types
template <typename T>
struct vector_to_python_list
{
  static PyObject* convert(std::vector<T> const& v)
  {
    using namespace std;
    using namespace boost::python;
    using boost::python::list;
    list l;
    typename vector<T>::const_iterator p;
    for(p=v.begin();p!=v.end();++p){
      l.append(object(*p));
    }
    return incref(l.ptr());
  }
};

template <typename T>
struct enum_to_python_int
{
  static PyObject* convert(T const& v)
  {
    using namespace std;
    using namespace boost::python;
    object l;
	 l = object(static_cast<int>(v));
    return incref(l.ptr());
  }
};
