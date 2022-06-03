from abc import abstractmethod

from foxes.core.data_calc_model import DataCalcModel

class PointDataModel(DataCalcModel):
    """
    Abstract base class for models that modify
    point based data.
    """

    @abstractmethod
    def output_point_vars(self, algo):
        """
        The variables which are being modified by the model.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        
        Returns
        -------
        output_vars : list of str
            The output variable names

        """
        return []
    
    @abstractmethod
    def calculate(self, algo, mdata, fdata, pdata):
        """"
        The main model calculation.

        This function is executed on a single chunk of data,
        all computations should be based on numpy arrays.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        mdata : foxes.core.Data
            The model data
        fdata : foxes.core.Data
            The farm data
        pdata : foxes.core.Data
            The point data
        
        Returns
        -------
        results : dict
            The resulting data, keys: output variable str.
            Values: numpy.ndarray with shape (n_states, n_points)

        """
        pass

    def finalize(self, algo, results, clear_mem=False):
        """
        Finalizes the model.

        Parameters
        ----------
        algo : foxes.core.Algorithm
            The calculation algorithm
        results : xarray.Dataset
            The calculation results
        clear_mem : bool
            Flag for deleting model data and
            resetting initialization flag
            
        """
        super().finalize(algo, clear_mem=clear_mem)
        