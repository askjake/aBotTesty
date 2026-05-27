import { App } from 'antd';
import axios from 'axios';
import { ZodError } from 'zod';
import { handleZodError } from '@shared/ui/utils/errors.utils';

const useHandleError = () => {
  const { notification } = App.useApp();

  return (error: any) => {
    console.log(error);
    if (axios.isAxiosError(error) || error?.response) {
      const title = 'API error';
      if (Array.isArray(error?.response?.data?.detail)) {
        error?.response?.data?.detail.forEach((item: any) => {
          notification.error({
            title,
            description: item.msg,
          });
        });
      } else {
        const description =
          error?.response?.data?.description ||
          error?.response?.data?.detail ||
          error?.message ||
          'Something went wrong';
        notification.error({
          title,
          description,
        });
      }
    } else if (error instanceof ZodError) {
      const formattedError = error.format();
      handleZodError({ error: formattedError, notification });
    } else {
      notification.error({
        title: 'Unknown internal error',
        description: 'Something went wrong',
      });
    }
  };
};

export default useHandleError;
